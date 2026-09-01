from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import AuthenticatedUser
from app.collaboration.models import Demand, DemandEvent, DemandVote, FeedbackEntry, FeedbackMessage
from app.collaboration.schemas import (
    DemandAdminUpdate,
    DemandCreate,
    DemandDeliveryFeedbackUpdate,
    DemandEventResponse,
    DemandResponse,
    DemandUpdate,
    DemandVoteResponse,
    FeedbackAdminUpdate,
    FeedbackCreate,
    FeedbackMessageResponse,
    FeedbackResponse,
)


DEMAND_OWNER_EDITABLE = {"pending", "needs_info"}
FEEDBACK_USER_ACTIVE = {"pending", "processing", "needs_info", "resolved"}
DELIVERY_FEEDBACK_LABELS = {
    "resolved": "已解决",
    "partially_resolved": "部分解决",
    "unresolved": "未解决",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _request_no() -> str:
    return f"REQ-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"


def create_feedback(db: Session, current: AuthenticatedUser, payload: FeedbackCreate) -> FeedbackResponse:
    item = FeedbackEntry(
        user_id=current.user.id,
        feedback_type=payload.feedback_type,
        page_title=payload.page_title.strip(),
        page_path=payload.page_path.strip(),
        content=payload.content.strip(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return feedback_response(db, item, current.user, current)


def _feedback_messages(db: Session, feedback_id: str) -> list[FeedbackMessageResponse]:
    rows = db.execute(
        select(FeedbackMessage, User)
        .outerjoin(User, User.id == FeedbackMessage.author_user_id)
        .where(FeedbackMessage.feedback_id == feedback_id)
        .order_by(FeedbackMessage.created_at.asc())
    ).all()
    return [
        FeedbackMessageResponse(
            message_id=message.id,
            author_name=user.display_name if user is not None else "平台管理员",
            author_role=message.author_role,
            content=message.content,
            created_at=message.created_at,
        )
        for message, user in rows
    ]


def feedback_response(
    db: Session,
    item: FeedbackEntry,
    user: User,
    current: AuthenticatedUser,
) -> FeedbackResponse:
    handler = db.get(User, item.handler_user_id) if item.handler_user_id else None
    is_owner = item.user_id == current.user.id
    return FeedbackResponse(
        feedback_id=item.id,
        user_id=user.employee_id,
        display_name=user.display_name,
        feedback_type=item.feedback_type,
        page_title=item.page_title,
        page_path=item.page_path,
        content=item.content,
        status=item.status,
        resolution=item.resolution,
        handler_name=handler.display_name if handler else "",
        messages=_feedback_messages(db, item.id),
        created_at=item.created_at,
        updated_at=item.updated_at,
        can_withdraw=is_owner and item.status in {"pending", "needs_info"},
        can_reply=is_owner and item.status in FEEDBACK_USER_ACTIVE,
    )


def list_my_feedback(db: Session, current: AuthenticatedUser) -> list[FeedbackResponse]:
    rows = db.execute(
        select(FeedbackEntry, User)
        .join(User, User.id == FeedbackEntry.user_id)
        .where(FeedbackEntry.user_id == current.user.id)
        .order_by(FeedbackEntry.updated_at.desc(), FeedbackEntry.created_at.desc())
    ).all()
    return [feedback_response(db, item, user, current) for item, user in rows]


def list_feedback(db: Session, current: AuthenticatedUser) -> list[FeedbackResponse]:
    rows = db.execute(
        select(FeedbackEntry, User)
        .join(User, User.id == FeedbackEntry.user_id)
        .order_by(FeedbackEntry.updated_at.desc(), FeedbackEntry.created_at.desc())
    ).all()
    return [feedback_response(db, item, user, current) for item, user in rows]


def _owned_feedback(db: Session, feedback_id: str, current: AuthenticatedUser) -> FeedbackEntry:
    item = db.get(FeedbackEntry, feedback_id)
    if item is None or item.user_id != current.user.id:
        raise HTTPException(status_code=404, detail="反馈不存在")
    return item


def add_feedback_message(
    db: Session,
    feedback_id: str,
    current: AuthenticatedUser,
    content: str,
) -> FeedbackResponse:
    item = _owned_feedback(db, feedback_id, current)
    if item.status not in FEEDBACK_USER_ACTIVE:
        raise HTTPException(status_code=409, detail="当前反馈状态不能继续补充")
    db.add(FeedbackMessage(
        feedback_id=item.id,
        author_user_id=current.user.id,
        author_role="user",
        content=content.strip(),
    ))
    if item.status == "resolved":
        item.status = "processing"
        item.resolved_at = None
    item.updated_at = _now()
    db.commit()
    db.refresh(item)
    return feedback_response(db, item, current.user, current)


def withdraw_feedback(db: Session, feedback_id: str, current: AuthenticatedUser) -> FeedbackResponse:
    item = _owned_feedback(db, feedback_id, current)
    if item.status not in {"pending", "needs_info"}:
        raise HTTPException(status_code=409, detail="反馈已进入处理流程，不能撤回")
    item.status = "withdrawn"
    item.withdrawn_at = _now()
    item.updated_at = item.withdrawn_at
    db.commit()
    db.refresh(item)
    return feedback_response(db, item, current.user, current)


def review_feedback(
    db: Session,
    feedback_id: str,
    current: AuthenticatedUser,
    payload: FeedbackAdminUpdate,
) -> FeedbackResponse:
    item = db.get(FeedbackEntry, feedback_id)
    if item is None:
        raise HTTPException(status_code=404, detail="反馈不存在")
    if item.status == "withdrawn":
        raise HTTPException(status_code=409, detail="用户已撤回该反馈")
    if payload.status == "needs_info" and not payload.reply.strip():
        raise HTTPException(status_code=400, detail="请说明需要用户补充的信息")
    item.status = payload.status
    item.resolution = payload.resolution.strip()
    item.handler_user_id = current.user.id
    item.updated_at = _now()
    item.resolved_at = item.updated_at if payload.status in {"resolved", "closed"} else None
    if payload.reply.strip():
        db.add(FeedbackMessage(
            feedback_id=item.id,
            author_user_id=current.user.id,
            author_role="admin",
            content=payload.reply.strip(),
        ))
    db.commit()
    db.refresh(item)
    submitter = db.get(User, item.user_id)
    return feedback_response(db, item, submitter, current)


def create_demand(db: Session, current: AuthenticatedUser, payload: DemandCreate) -> Demand:
    item = Demand(
        request_no=_request_no(),
        user_id=current.user.id,
        title=payload.title.strip(),
        domain=payload.domain.strip(),
        expected_time=payload.expected_time.strip(),
        background=payload.background.strip(),
        description=payload.description.strip(),
        business_value=payload.business_value.strip(),
        contact=payload.contact.strip() or current.user.employee_id,
    )
    db.add(item)
    db.flush()
    db.add(DemandEvent(
        demand_id=item.id,
        actor_user_id=current.user.id,
        actor_role="user",
        event_type="submitted",
        to_status="pending",
        comment="提交需求，等待平台审视",
    ))
    db.commit()
    db.refresh(item)
    return item


def _demand_history(db: Session, demand_id: str) -> list[DemandEventResponse]:
    rows = db.execute(
        select(DemandEvent, User)
        .outerjoin(User, User.id == DemandEvent.actor_user_id)
        .where(DemandEvent.demand_id == demand_id)
        .order_by(DemandEvent.created_at.asc())
    ).all()
    return [
        DemandEventResponse(
            event_id=event.id,
            actor_name=user.display_name if user is not None else "平台管理员",
            actor_role=event.actor_role,
            event_type=event.event_type,
            from_status=event.from_status,
            to_status=event.to_status,
            comment=event.comment,
            created_at=event.created_at,
        )
        for event, user in rows
    ]


def _is_visible(item: Demand, current: AuthenticatedUser) -> bool:
    return current.is_admin_mode or item.user_id == current.user.id or item.visibility == "public"


def demand_response(db: Session, item: Demand, submitter: User, current: AuthenticatedUser) -> DemandResponse:
    support_count = db.scalar(
        select(func.count()).select_from(DemandVote).where(DemandVote.demand_id == item.id)
    ) or 0
    voted = db.scalar(select(DemandVote.id).where(
        DemandVote.demand_id == item.id,
        DemandVote.user_id == current.user.id,
    )) is not None
    handler = db.get(User, item.handler_user_id) if item.handler_user_id else None
    is_own = item.user_id == current.user.id
    return DemandResponse(
        demand_id=item.id,
        request_no=item.request_no,
        submitter_id=submitter.employee_id,
        submitter_name=submitter.display_name,
        title=item.title,
        domain=item.domain,
        expected_time=item.expected_time,
        background=item.background,
        description=item.description,
        business_value=item.business_value,
        contact=item.contact,
        status=item.status,
        conclusion=item.conclusion,
        visibility=item.visibility,
        priority=item.priority,
        planned_time=item.planned_time,
        handler_name=handler.display_name if handler else "",
        support_count=int(support_count),
        voted_by_me=voted,
        is_own=is_own,
        created_at=item.created_at,
        updated_at=item.updated_at,
        delivery_feedback=item.delivery_feedback,
        delivery_feedback_at=item.delivery_feedback_at,
        can_edit=is_own and item.status in DEMAND_OWNER_EDITABLE,
        can_withdraw=is_own and item.status in DEMAND_OWNER_EDITABLE and int(support_count) == 0,
        history=_demand_history(db, item.id),
    )


def list_demands(db: Session, current: AuthenticatedUser, scope: str = "public") -> list[DemandResponse]:
    query = select(Demand, User).join(User, User.id == Demand.user_id)
    if scope == "mine":
        query = query.where(Demand.user_id == current.user.id)
    elif scope == "public":
        query = query.where(Demand.visibility == "public")
    elif scope == "all":
        if not current.is_admin_mode:
            raise HTTPException(status_code=403, detail="需要管理员身份")
    else:
        raise HTTPException(status_code=400, detail="不支持的需求列表范围")
    rows = db.execute(query.order_by(Demand.updated_at.desc(), Demand.created_at.desc())).all()
    return [demand_response(db, item, user, current) for item, user in rows]


def get_visible_demand(db: Session, demand_id: str, current: AuthenticatedUser) -> tuple[Demand, User]:
    row = db.execute(
        select(Demand, User).join(User, User.id == Demand.user_id).where(Demand.id == demand_id)
    ).first()
    if row is None or not _is_visible(row[0], current):
        raise HTTPException(status_code=404, detail="需求不存在或当前不可见")
    return row[0], row[1]


def update_demand(
    db: Session,
    demand_id: str,
    current: AuthenticatedUser,
    payload: DemandUpdate,
) -> DemandResponse:
    item, submitter = get_visible_demand(db, demand_id, current)
    if item.user_id != current.user.id or item.status not in DEMAND_OWNER_EDITABLE:
        raise HTTPException(status_code=409, detail="当前需求不能修改")
    for field in ("title", "domain", "expected_time", "background", "description", "business_value", "contact"):
        setattr(item, field, getattr(payload, field).strip())
    item.updated_at = _now()
    db.add(DemandEvent(
        demand_id=item.id,
        actor_user_id=current.user.id,
        actor_role="user",
        event_type="updated",
        from_status=item.status,
        to_status=item.status,
        comment="提交人更新了需求内容",
    ))
    db.commit()
    db.refresh(item)
    return demand_response(db, item, submitter, current)


def withdraw_demand(db: Session, demand_id: str, current: AuthenticatedUser) -> DemandResponse:
    item, submitter = get_visible_demand(db, demand_id, current)
    support_count = db.scalar(
        select(func.count()).select_from(DemandVote).where(DemandVote.demand_id == item.id)
    ) or 0
    if item.user_id != current.user.id or item.status not in DEMAND_OWNER_EDITABLE or support_count:
        raise HTTPException(status_code=409, detail="需求已进入平台处理或已有支持者，不能撤回")
    previous = item.status
    item.status = "withdrawn"
    item.visibility = "private"
    item.withdrawn_at = _now()
    item.updated_at = item.withdrawn_at
    db.add(DemandEvent(
        demand_id=item.id,
        actor_user_id=current.user.id,
        actor_role="user",
        event_type="withdrawn",
        from_status=previous,
        to_status="withdrawn",
        comment="提交人撤回需求",
    ))
    db.commit()
    db.refresh(item)
    return demand_response(db, item, submitter, current)


def set_delivery_feedback(
    db: Session,
    demand_id: str,
    current: AuthenticatedUser,
    payload: DemandDeliveryFeedbackUpdate,
) -> DemandResponse:
    item, submitter = get_visible_demand(db, demand_id, current)
    if item.user_id != current.user.id:
        raise HTTPException(status_code=403, detail="仅需求提交人可以反馈交付结果")
    if item.status != "delivered":
        raise HTTPException(status_code=409, detail="需求交付后才可以反馈解决情况")

    item.delivery_feedback = payload.resolution
    item.delivery_feedback_at = _now()
    item.updated_at = item.delivery_feedback_at
    db.add(DemandEvent(
        demand_id=item.id,
        actor_user_id=current.user.id,
        actor_role="user",
        event_type="delivery_feedback",
        from_status=item.status,
        to_status=item.status,
        comment=f"提交人反馈：{DELIVERY_FEEDBACK_LABELS[payload.resolution]}",
    ))
    db.commit()
    db.refresh(item)
    return demand_response(db, item, submitter, current)


def review_demand(
    db: Session,
    demand_id: str,
    current: AuthenticatedUser,
    payload: DemandAdminUpdate,
) -> DemandResponse:
    item = db.get(Demand, demand_id)
    if item is None:
        raise HTTPException(status_code=404, detail="需求不存在")
    if item.status == "withdrawn":
        raise HTTPException(status_code=409, detail="提交人已撤回该需求")
    if payload.status in {"needs_info", "deferred", "rejected"} and not payload.conclusion.strip():
        raise HTTPException(status_code=400, detail="当前处理结果需要填写审视说明")
    previous = item.status
    item.status = payload.status
    item.conclusion = payload.conclusion.strip()
    item.visibility = payload.visibility
    item.priority = payload.priority
    item.planned_time = payload.planned_time.strip()
    item.handler_user_id = current.user.id
    if item.status != "delivered":
        item.delivery_feedback = None
        item.delivery_feedback_at = None
    item.updated_at = _now()
    db.add(DemandEvent(
        demand_id=item.id,
        actor_user_id=current.user.id,
        actor_role="admin",
        event_type="reviewed" if previous == "pending" else "status_changed",
        from_status=previous,
        to_status=item.status,
        comment=item.conclusion or "平台更新了需求处理状态",
    ))
    db.commit()
    db.refresh(item)
    submitter = db.get(User, item.user_id)
    return demand_response(db, item, submitter, current)


def set_vote(db: Session, item: Demand, current: AuthenticatedUser, enabled: bool) -> DemandVoteResponse:
    if item.visibility != "public" or item.status == "withdrawn":
        raise HTTPException(status_code=409, detail="当前需求不支持投票")
    existing = db.scalar(select(DemandVote).where(
        DemandVote.demand_id == item.id,
        DemandVote.user_id == current.user.id,
    ))
    if enabled and existing is None:
        db.add(DemandVote(demand_id=item.id, user_id=current.user.id))
    elif not enabled and existing is not None:
        db.execute(delete(DemandVote).where(DemandVote.id == existing.id))
    db.commit()
    count = db.scalar(
        select(func.count()).select_from(DemandVote).where(DemandVote.demand_id == item.id)
    ) or 0
    return DemandVoteResponse(demand_id=item.id, support_count=int(count), voted_by_me=enabled)
