from datetime import datetime, timezone
from string import Formatter
from urllib.parse import quote
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analytics.schemas import AnalyticsEventCreate
from app.auth.constants import BENCHMARK_ACCESS_PERMISSION
from app.auth.models import User
from app.auth.service import AuthenticatedUser, get_user_permissions
from app.common.config import Settings
from app.recent_activity.config import load_recent_activity_config
from app.recent_activity.models import RecentActivity
from app.recent_activity.schemas import (
    RecentActivityEventConfig,
    RecentActivityItem,
    RecentActivityListResponse,
)
from app.simulation.models import SimulationTask


SHANGHAI = ZoneInfo("Asia/Shanghai")


def _context(payload: AnalyticsEventCreate) -> dict[str, str]:
    values = payload.model_dump()
    return {
        key: str(value)
        for key, value in values.items()
        if value is not None and value != "" and key not in {"event_id", "session_id"}
    }


def _render(template: str, values: dict[str, str], *, encode: bool = False) -> str:
    parts: list[str] = []
    for literal, field_name, format_spec, conversion in Formatter().parse(template):
        if format_spec or conversion:
            raise ValueError("format specifications are not supported in recent activity templates")
        parts.append(literal)
        if field_name is not None:
            if field_name not in values:
                raise KeyError(field_name)
            value = values[field_name]
            parts.append(quote(value, safe="") if encode else value)
    return "".join(parts)


def project_recent_activity(
    db: Session,
    user: User,
    payload: AnalyticsEventCreate,
    settings: Settings,
) -> None:
    config = load_recent_activity_config(settings.platform_recent_activity_config)
    event_config = config.events.get(payload.event_name)
    if event_config is None or not event_config.enabled:
        return

    values = _context(payload)
    target_type = values.get("target_type", "")
    target_id = values.get("target_id", "")
    target_name = values.get("target_name", "")
    if not target_type or not target_id or not target_name:
        return

    # Serialize projection updates per user so concurrent analytics requests cannot
    # create duplicate dedupe keys or temporarily retain more than the configured cap.
    with db.no_autoflush:
        db.scalar(select(User.id).where(User.id == user.id).with_for_update())

    if target_type == "simulation_task":
        task = db.scalar(select(SimulationTask).where(
            SimulationTask.task_id == target_id,
            SimulationTask.owner_id == user.employee_id,
        ))
        if task is None:
            return
        values["target_name"] = task.task_name
        target_name = task.task_name

    try:
        dedupe_key = _render(event_config.dedupe_key, values)
    except (KeyError, ValueError):
        return

    item = db.scalar(select(RecentActivity).where(
        RecentActivity.user_id == user.id,
        RecentActivity.dedupe_key == dedupe_key,
    ))
    now = datetime.now(timezone.utc)
    if item is None:
        item = RecentActivity(user_id=user.id, dedupe_key=dedupe_key)
        db.add(item)
    item.event_name = payload.event_name
    item.target_type = target_type
    item.target_id = target_id
    item.target_name = target_name
    item.context = values
    item.last_occurred_at = now
    db.flush()

    overflow_ids = list(db.scalars(
        select(RecentActivity.id)
        .where(RecentActivity.user_id == user.id)
        .order_by(RecentActivity.last_occurred_at.desc(), RecentActivity.id.desc())
        .offset(config.home.storage_limit)
    ).all())
    if overflow_ids:
        db.execute(delete(RecentActivity).where(RecentActivity.id.in_(overflow_ids)))


def _relative_time(value: datetime) -> str:
    occurred = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    seconds = max(int((datetime.now(timezone.utc) - occurred).total_seconds()), 0)
    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{seconds // 60}分钟前"
    if seconds < 86400:
        return f"{seconds // 3600}小时前"
    if seconds < 86400 * 7:
        return f"{seconds // 86400}天前"
    return occurred.astimezone(SHANGHAI).strftime("%Y-%m-%d")


def _target_is_visible(db: Session, current: AuthenticatedUser, item: RecentActivity) -> bool:
    if item.target_type == "simulation_task":
        return db.scalar(select(SimulationTask.task_id).where(
            SimulationTask.task_id == item.target_id,
            SimulationTask.owner_id == current.user.employee_id,
        )) is not None
    if item.target_type in {"benchmark", "benchmark_chip"}:
        return current.is_admin_mode or BENCHMARK_ACCESS_PERMISSION in get_user_permissions(db, current)
    return False


def list_recent_activities(
    db: Session,
    current: AuthenticatedUser,
    settings: Settings,
) -> RecentActivityListResponse:
    config = load_recent_activity_config(settings.platform_recent_activity_config)
    rows = list(db.scalars(
        select(RecentActivity)
        .where(RecentActivity.user_id == current.user.id)
        .order_by(RecentActivity.last_occurred_at.desc(), RecentActivity.id.desc())
        .limit(config.home.storage_limit)
    ).all())

    items: list[RecentActivityItem] = []
    for row in rows:
        event_config: RecentActivityEventConfig | None = config.events.get(row.event_name)
        if event_config is None or not event_config.enabled or not _target_is_visible(db, current, row):
            continue
        values = {key: str(value) for key, value in row.context.items() if value is not None}
        values.update({
            "target_type": row.target_type,
            "target_id": row.target_id,
            "target_name": row.target_name,
            "relative_time": _relative_time(row.last_occurred_at),
        })
        try:
            items.append(RecentActivityItem(
                id=row.id,
                event_name=row.event_name,
                domain=event_config.domain,
                icon=event_config.icon,
                title=_render(event_config.title_template, values),
                description=_render(event_config.description_template, values),
                action_label=event_config.action_label,
                href=_render(event_config.route, values, encode=True),
                occurred_at=row.last_occurred_at,
            ))
        except (KeyError, ValueError):
            continue
        if len(items) >= config.home.display_limit:
            break

    return RecentActivityListResponse(
        title=config.home.title,
        description=config.home.description,
        empty_text=config.home.empty_text,
        items=items,
    )
