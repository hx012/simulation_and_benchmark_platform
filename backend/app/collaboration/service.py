from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import AuthenticatedUser
from app.collaboration.content import load_demand_reviews
from app.collaboration.models import Demand, DemandVote, FeedbackEntry
from app.collaboration.schemas import DemandCreate, DemandResponse, DemandVoteResponse, FeedbackCreate, FeedbackResponse
from app.common.config import Settings


def _request_no() -> str:
    day = datetime.now().strftime("%Y%m%d")
    return f"REQ-{day}-{uuid4().hex[:6].upper()}"


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
    return feedback_response(item, current.user)


def feedback_response(item: FeedbackEntry, user: User) -> FeedbackResponse:
    return FeedbackResponse(
        feedback_id=item.id,
        user_id=user.employee_id,
        display_name=user.display_name,
        feedback_type=item.feedback_type,
        page_title=item.page_title,
        page_path=item.page_path,
        content=item.content,
        status=item.status,
        created_at=item.created_at,
    )


def list_feedback(db: Session) -> list[FeedbackResponse]:
    rows = db.execute(
        select(FeedbackEntry, User)
        .join(User, User.id == FeedbackEntry.user_id)
        .order_by(FeedbackEntry.created_at.desc())
    ).all()
    return [feedback_response(item, user) for item, user in rows]


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
    db.commit()
    db.refresh(item)
    return item


def _review_for(item: Demand, settings: Settings, reviews: dict[str, dict] | None = None) -> dict:
    source = reviews if reviews is not None else load_demand_reviews(settings)
    review = source.get(item.request_no, {})
    return review if isinstance(review, dict) else {}


def _is_visible(
    item: Demand,
    current: AuthenticatedUser,
    settings: Settings,
    reviews: dict[str, dict] | None = None,
) -> bool:
    if current.is_admin_mode or item.user_id == current.user.id:
        return True
    return str(_review_for(item, settings, reviews).get("visibility", "private")) == "public"


def demand_response(
    db: Session,
    item: Demand,
    submitter: User,
    current: AuthenticatedUser,
    settings: Settings,
    review: dict | None = None,
) -> DemandResponse:
    review = review if review is not None else _review_for(item, settings)
    support_count = db.scalar(select(func.count()).select_from(DemandVote).where(DemandVote.demand_id == item.id)) or 0
    voted = db.scalar(select(DemandVote.id).where(
        DemandVote.demand_id == item.id, DemandVote.user_id == current.user.id
    )) is not None
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
        status=str(review.get("status", "pending")),
        conclusion=str(review.get("conclusion", "")),
        visibility=str(review.get("visibility", "private")),
        support_count=int(support_count),
        voted_by_me=voted,
        is_own=item.user_id == current.user.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def list_demands(db: Session, current: AuthenticatedUser, settings: Settings) -> list[DemandResponse]:
    reviews = load_demand_reviews(settings)
    rows = db.execute(
        select(Demand, User).join(User, User.id == Demand.user_id).order_by(Demand.created_at.desc())
    ).all()
    return [
        demand_response(db, item, user, current, settings, _review_for(item, settings, reviews))
        for item, user in rows
        if _is_visible(item, current, settings, reviews)
    ]


def get_visible_demand(db: Session, demand_id: str, current: AuthenticatedUser, settings: Settings) -> tuple[Demand, User]:
    row = db.execute(
        select(Demand, User).join(User, User.id == Demand.user_id).where(Demand.id == demand_id)
    ).first()
    if row is None or not _is_visible(row[0], current, settings):
        raise HTTPException(status_code=404, detail="需求不存在或当前不可见")
    return row[0], row[1]


def set_vote(db: Session, item: Demand, current: AuthenticatedUser, enabled: bool) -> DemandVoteResponse:
    existing = db.scalar(select(DemandVote).where(
        DemandVote.demand_id == item.id, DemandVote.user_id == current.user.id
    ))
    if enabled and existing is None:
        db.add(DemandVote(demand_id=item.id, user_id=current.user.id))
    elif not enabled and existing is not None:
        db.execute(delete(DemandVote).where(DemandVote.id == existing.id))
    db.commit()
    count = db.scalar(select(func.count()).select_from(DemandVote).where(DemandVote.demand_id == item.id)) or 0
    return DemandVoteResponse(demand_id=item.id, support_count=int(count), voted_by_me=enabled)
