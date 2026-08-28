from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.models import AnalyticsEvent
from app.auth.models import User
from app.auth.service import AuthenticatedUser
from app.collaboration.models import TeamAchievementRecord
from app.collaboration.schemas import (
    TeamAchievementCreate,
    TeamAchievementRepresentativeUpdate,
    TeamAchievementResponse,
    TeamAchievementScoreUpdate,
    TeamAchievementUpdate,
)


def can_view_archives(current: AuthenticatedUser, visibility: str = "team_only") -> bool:
    return visibility == "authenticated" or current.is_admin_mode or current.user.is_team_member


def require_archive_access(current: AuthenticatedUser, visibility: str = "team_only") -> None:
    if not can_view_archives(current, visibility):
        raise HTTPException(status_code=403, detail="仅团队成员可看")


def require_archive_editor(current: AuthenticatedUser) -> None:
    if current.is_admin_mode:
        raise HTTPException(status_code=403, detail="管理员登录模式仅可评分和评价成果")
    if not current.user.is_team_member:
        raise HTTPException(status_code=403, detail="仅团队成员可以维护成果档案")


def _user_by_employee_id(db: Session, employee_id: str) -> User:
    user = db.scalar(select(User).where(User.employee_id == employee_id.strip()))
    if user is None:
        raise HTTPException(status_code=404, detail="成员账号不存在")
    return user


def _record_team_event(
    db: Session,
    current: AuthenticatedUser,
    event_name: str,
    owner: User,
    item: TeamAchievementRecord | None = None,
    change_summary: str = "",
) -> None:
    db.add(AnalyticsEvent(
        event_id=str(uuid4()),
        user_id=current.user.id,
        session_id=current.session.id or current.session.token_hash,
        event_name=event_name,
        page_key="team",
        result="success",
        target_type="team_achievement" if item is not None else "team_achievement_archive",
        target_id=item.id if item is not None else owner.employee_id,
        target_name=item.title if item is not None else f"{owner.display_name}的成果档案",
        target_user_id=owner.employee_id,
        auth_mode=current.session.auth_mode,
        change_summary=change_summary[:1000],
    ))


def achievement_response(
    db: Session,
    item: TeamAchievementRecord,
    owner: User,
    current: AuthenticatedUser,
) -> TeamAchievementResponse:
    scorer = db.get(User, item.scored_by_user_id) if item.scored_by_user_id else None
    editable = (
        not current.is_admin_mode
        and current.user.is_team_member
        and item.owner_user_id == current.user.id
    )
    return TeamAchievementResponse(
        achievement_id=item.id,
        owner_employee_id=owner.employee_id,
        owner_name=owner.display_name,
        title=item.title,
        category=item.category,
        summary=item.summary,
        completion_date=item.completion_date,
        reference_url=item.reference_url,
        representative=item.representative,
        score=item.score,
        evaluation=item.evaluation,
        scored_by_employee_id=scorer.employee_id if scorer else "",
        scored_by_name=scorer.display_name if scorer else "",
        scored_at=item.scored_at,
        can_edit=editable,
        can_delete=editable,
        can_score=current.is_admin_mode,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def list_achievements(
    db: Session,
    current: AuthenticatedUser,
    employee_id: str,
    visibility: str = "team_only",
) -> list[TeamAchievementResponse]:
    require_archive_access(current, visibility)
    owner = _user_by_employee_id(db, employee_id)
    items = db.scalars(
        select(TeamAchievementRecord)
        .where(TeamAchievementRecord.owner_user_id == owner.id)
        .order_by(TeamAchievementRecord.completion_date.desc(), TeamAchievementRecord.created_at.desc())
    ).all()
    response = [achievement_response(db, item, owner, current) for item in items]
    _record_team_event(db, current, "team.achievement_archive_view", owner)
    db.commit()
    return response


def create_achievement(
    db: Session,
    current: AuthenticatedUser,
    payload: TeamAchievementCreate,
) -> TeamAchievementResponse:
    require_archive_editor(current)
    owner = current.user
    if payload.owner_employee_id.strip() and payload.owner_employee_id.strip() != owner.employee_id:
        raise HTTPException(status_code=403, detail="只能登记自己的成果")
    item = TeamAchievementRecord(
        owner_user_id=owner.id,
        title=payload.title.strip(),
        category=payload.category.strip(),
        summary=payload.summary.strip(),
        completion_date=payload.completion_date,
        reference_url=payload.reference_url.strip(),
        representative=False,
    )
    db.add(item)
    db.flush()
    _record_team_event(db, current, "team.achievement_create", owner, item, "新增成果")
    db.commit()
    db.refresh(item)
    return achievement_response(db, item, owner, current)


def _achievement_item(db: Session, achievement_id: str) -> tuple[TeamAchievementRecord, User]:
    item = db.get(TeamAchievementRecord, achievement_id)
    if item is None:
        raise HTTPException(status_code=404, detail="成果不存在")
    owner = db.get(User, item.owner_user_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="成果成员不存在")
    return item, owner


def _editable_item(db: Session, current: AuthenticatedUser, achievement_id: str) -> tuple[TeamAchievementRecord, User]:
    item, owner = _achievement_item(db, achievement_id)
    if item.owner_user_id != current.user.id:
        raise HTTPException(status_code=403, detail="只能维护自己的成果")
    return item, owner


def update_achievement(
    db: Session,
    current: AuthenticatedUser,
    achievement_id: str,
    payload: TeamAchievementUpdate,
) -> TeamAchievementResponse:
    require_archive_editor(current)
    item, owner = _editable_item(db, current, achievement_id)
    changed_fields: list[str] = []
    values = {
        "title": payload.title.strip(),
        "category": payload.category.strip(),
        "summary": payload.summary.strip(),
        "completion_date": payload.completion_date,
        "reference_url": payload.reference_url.strip(),
    }
    labels = {
        "title": "标题", "category": "类型", "summary": "成果内容",
        "completion_date": "完成日期", "reference_url": "关联材料",
    }
    for field, value in values.items():
        if getattr(item, field) != value:
            changed_fields.append(labels[field])
            setattr(item, field, value)
    _record_team_event(
        db, current, "team.achievement_update", owner, item,
        f"修改字段：{'、'.join(changed_fields)}" if changed_fields else "保存成果（无字段变化）",
    )
    db.commit()
    db.refresh(item)
    return achievement_response(db, item, owner, current)


def set_representative(
    db: Session,
    current: AuthenticatedUser,
    achievement_id: str,
    payload: TeamAchievementRepresentativeUpdate,
) -> TeamAchievementResponse:
    require_archive_editor(current)
    item, owner = _editable_item(db, current, achievement_id)
    item.representative = payload.representative
    _record_team_event(
        db,
        current,
        "team.achievement_core_set" if payload.representative else "team.achievement_core_unset",
        owner,
        item,
        "设为核心成果" if payload.representative else "取消核心成果",
    )
    db.commit()
    db.refresh(item)
    return achievement_response(db, item, owner, current)


def delete_achievement(db: Session, current: AuthenticatedUser, achievement_id: str) -> None:
    require_archive_editor(current)
    item, owner = _editable_item(db, current, achievement_id)
    _record_team_event(db, current, "team.achievement_delete", owner, item, "删除成果")
    db.delete(item)
    db.commit()


def score_achievement(
    db: Session,
    current: AuthenticatedUser,
    achievement_id: str,
    payload: TeamAchievementScoreUpdate,
) -> TeamAchievementResponse:
    if not current.is_admin_mode:
        raise HTTPException(status_code=403, detail="只有管理员可以评分和评价")
    item, owner = _achievement_item(db, achievement_id)
    previous_score = item.score
    previous_evaluation = item.evaluation
    item.score = payload.score
    item.evaluation = payload.evaluation
    item.scored_by_user_id = current.user.id if payload.score is not None else None
    item.scored_at = datetime.now(timezone.utc) if payload.score is not None else None
    changes = [f"评分：{previous_score if previous_score is not None else '未评分'}→{payload.score if payload.score is not None else '未评分'}"]
    if previous_evaluation != payload.evaluation:
        changes.append("评价已更新" if payload.evaluation else "评价已清除")
    _record_team_event(db, current, "team.achievement_score", owner, item, "；".join(changes))
    db.commit()
    db.refresh(item)
    return achievement_response(db, item, owner, current)


def enrich_team_members(db: Session, current: AuthenticatedUser, team) -> None:
    team.viewer_is_team_member = current.user.is_team_member
    team.viewer_is_admin = current.is_admin_mode
    team.viewer_can_view_archives = can_view_archives(current, team.archive_visibility)
    employee_ids = [member.employee_id for member in team.members]
    if not employee_ids:
        return
    users = db.scalars(select(User).where(User.employee_id.in_(employee_ids))).all()
    by_employee = {user.employee_id: user for user in users}
    for member in team.members:
        user = by_employee.get(member.employee_id)
        member.is_team_member = bool(user and user.is_team_member)
        if user is None:
            continue
        member.representative_achievements = list(db.scalars(
            select(TeamAchievementRecord.title)
            .where(
                TeamAchievementRecord.owner_user_id == user.id,
                TeamAchievementRecord.representative.is_(True),
            )
            .order_by(TeamAchievementRecord.completion_date.desc(), TeamAchievementRecord.created_at.desc())
        ).all())
        member.latest_completion_date = db.scalar(
            select(func.max(TeamAchievementRecord.completion_date)).where(
                TeamAchievementRecord.owner_user_id == user.id,
                TeamAchievementRecord.representative.is_(True),
            )
        )
