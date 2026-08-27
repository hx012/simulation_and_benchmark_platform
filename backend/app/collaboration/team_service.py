from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import AuthenticatedUser
from app.collaboration.models import TeamAchievementRecord
from app.collaboration.schemas import (
    TeamAchievementCreate,
    TeamAchievementResponse,
    TeamAchievementUpdate,
)


def can_view_archives(current: AuthenticatedUser, visibility: str = "team_only") -> bool:
    return visibility == "authenticated" or current.is_admin_mode or current.user.is_team_member


def require_archive_access(current: AuthenticatedUser, visibility: str = "team_only") -> None:
    if not can_view_archives(current, visibility):
        raise HTTPException(status_code=403, detail="仅团队成员可看")


def require_archive_editor(current: AuthenticatedUser) -> None:
    if not current.is_admin_mode and not current.user.is_team_member:
        raise HTTPException(status_code=403, detail="仅团队成员可以维护成果档案")


def _user_by_employee_id(db: Session, employee_id: str) -> User:
    user = db.scalar(select(User).where(User.employee_id == employee_id.strip()))
    if user is None:
        raise HTTPException(status_code=404, detail="成员账号不存在")
    return user


def achievement_response(
    item: TeamAchievementRecord,
    owner: User,
    current: AuthenticatedUser,
) -> TeamAchievementResponse:
    editable = current.is_admin_mode or (
        current.user.is_team_member and item.owner_user_id == current.user.id
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
    return [achievement_response(item, owner, current) for item in items]


def create_achievement(
    db: Session,
    current: AuthenticatedUser,
    payload: TeamAchievementCreate,
) -> TeamAchievementResponse:
    require_archive_editor(current)
    owner = current.user
    if current.is_admin_mode and payload.owner_employee_id.strip():
        owner = _user_by_employee_id(db, payload.owner_employee_id)
    elif payload.owner_employee_id.strip() and payload.owner_employee_id.strip() != current.user.employee_id:
        raise HTTPException(status_code=403, detail="只能登记自己的成果")
    if not owner.is_team_member:
        raise HTTPException(status_code=403, detail="只能为已标记的团队成员登记成果")
    item = TeamAchievementRecord(
        owner_user_id=owner.id,
        title=payload.title.strip(),
        category=payload.category.strip(),
        summary=payload.summary.strip(),
        completion_date=payload.completion_date,
        reference_url=payload.reference_url.strip(),
        representative=payload.representative,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return achievement_response(item, owner, current)


def _editable_item(db: Session, current: AuthenticatedUser, achievement_id: str) -> tuple[TeamAchievementRecord, User]:
    item = db.get(TeamAchievementRecord, achievement_id)
    if item is None:
        raise HTTPException(status_code=404, detail="成果不存在")
    owner = db.get(User, item.owner_user_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="成果成员不存在")
    if not current.is_admin_mode and item.owner_user_id != current.user.id:
        raise HTTPException(status_code=403, detail="只能维护自己的成果")
    return item, owner


def update_achievement(db: Session, current: AuthenticatedUser, achievement_id: str, payload: TeamAchievementUpdate) -> TeamAchievementResponse:
    require_archive_editor(current)
    item, owner = _editable_item(db, current, achievement_id)
    item.title = payload.title.strip()
    item.category = payload.category.strip()
    item.summary = payload.summary.strip()
    item.completion_date = payload.completion_date
    item.reference_url = payload.reference_url.strip()
    item.representative = payload.representative
    db.commit()
    db.refresh(item)
    return achievement_response(item, owner, current)


def delete_achievement(db: Session, current: AuthenticatedUser, achievement_id: str) -> None:
    require_archive_editor(current)
    item, _ = _editable_item(db, current, achievement_id)
    db.delete(item)
    db.commit()


def score_achievement(db: Session, current: AuthenticatedUser, achievement_id: str, score: int | None) -> TeamAchievementResponse:
    if not current.is_admin_mode:
        raise HTTPException(status_code=403, detail="只有管理员可以评分")
    item, owner = _editable_item(db, current, achievement_id)
    item.score = score
    db.commit()
    db.refresh(item)
    return achievement_response(item, owner, current)


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
            select(func.max(TeamAchievementRecord.completion_date))
            .where(TeamAchievementRecord.owner_user_id == user.id)
        )
