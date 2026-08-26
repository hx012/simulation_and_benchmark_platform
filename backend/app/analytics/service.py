from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import logging
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.analytics.models import AnalyticsEvent
from app.analytics.schemas import (
    AnalyticsEventCreate,
    AnalyticsOverviewResponse,
    AnalyticsRankingItem,
    AnalyticsSimulationDimensionItem,
    AnalyticsSummary,
    AnalyticsTrendPoint,
    AnalyticsUserDetailResponse,
    AnalyticsUserEventItem,
    AnalyticsUserItem,
    AnalyticsUserListResponse,
    AnalyticsUserPageItem,
)
from app.auth.models import User
from app.collaboration.models import Demand, FeedbackEntry
from app.common.config import get_settings
from app.recent_activity.service import project_recent_activity
from app.simulation.enums import TaskStatus
from app.simulation.models import SimulationTask


SHANGHAI = ZoneInfo("Asia/Shanghai")
logger = logging.getLogger(__name__)

PAGE_LABELS = {
    "home": "首页",
    "simulation.create": "新建仿真任务",
    "simulation.tasks": "我的任务",
    "simulation.task_detail": "仿真任务详情",
    "simulation.task_result": "仿真结果",
    "benchmark.browse": "Benchmark 浏览",
    "benchmark.chip": "芯片 Benchmark",
    "benchmark.detail": "Benchmark 详情",
    "performance.workspace": "性能分析工作台",
    "team": "团队风采",
    "demands": "需求池",
    "permissions": "权限中心",
    "analytics.usage": "使用分析",
}

EVENT_LABELS = {
    "page_view": "页面访问",
    "page_active_time": "页面有效停留",
    "simulation.task_create_success": "创建仿真任务",
    "simulation.task_create_failed": "创建仿真任务失败",
    "simulation.task_rerun": "重新运行仿真任务",
    "simulation.result_view": "查看仿真结果",
    "benchmark.chip_view": "查看芯片 Benchmark",
    "benchmark.detail_view": "查看 Benchmark 详情",
    "performance.trace_analyze_success": "Trace 时间分析",
    "demand.create": "提交需求",
    "demand.vote": "需求投票",
    "feedback.submit": "提交反馈",
}

FEATURE_EVENTS = set(EVENT_LABELS) - {"page_view", "page_active_time"}


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _range(days: int) -> tuple[datetime, datetime]:
    end_at = datetime.now(timezone.utc)
    return end_at - timedelta(days=days), end_at


def create_event(db: Session, user: User, payload: AnalyticsEventCreate) -> None:
    event = AnalyticsEvent(user_id=user.id, **payload.model_dump())
    db.add(event)
    try:
        try:
            with db.begin_nested():
                project_recent_activity(db, user, payload, get_settings())
        except Exception:
            # Recent work is a convenience projection; its configuration or write
            # failure must never discard the source analytics event.
            logger.exception("Failed to project recent activity event=%s", payload.event_name)
        db.commit()
    except IntegrityError:
        db.rollback()
        # Client retries are idempotent by event_id.


def delete_expired_events(
    db: Session,
    retention_days: int,
    *,
    now: datetime | None = None,
) -> int:
    """Delete raw behavior events older than the configured retention period."""
    if retention_days < 1:
        return 0
    cutoff = _as_utc(now or datetime.now(timezone.utc)) - timedelta(days=retention_days)
    result = db.execute(
        delete(AnalyticsEvent).where(AnalyticsEvent.occurred_at < cutoff)
    )
    return max(int(result.rowcount or 0), 0)


def _events_in_range(db: Session, start_at: datetime, end_at: datetime) -> list[AnalyticsEvent]:
    return list(db.scalars(
        select(AnalyticsEvent)
        .where(AnalyticsEvent.occurred_at >= start_at, AnalyticsEvent.occurred_at <= end_at)
        .order_by(AnalyticsEvent.occurred_at.asc())
    ).all())


def _business_counts(db: Session, start_at: datetime, end_at: datetime) -> tuple[int, int]:
    task_count = db.scalar(
        select(func.count()).select_from(SimulationTask).where(
            SimulationTask.submit_time >= start_at,
            SimulationTask.submit_time <= end_at,
        )
    ) or 0
    demand_count = db.scalar(
        select(func.count()).select_from(Demand).where(
            Demand.created_at >= start_at, Demand.created_at <= end_at
        )
    ) or 0
    feedback_count = db.scalar(
        select(func.count()).select_from(FeedbackEntry).where(
            FeedbackEntry.created_at >= start_at, FeedbackEntry.created_at <= end_at
        )
    ) or 0
    return int(task_count), int(demand_count + feedback_count)


def _ranking(
    events: list[AnalyticsEvent],
    *,
    key_for,
    label_for,
    include,
    limit: int = 10,
) -> list[AnalyticsRankingItem]:
    groups: dict[str, list[AnalyticsEvent]] = defaultdict(list)
    for event in events:
        if include(event):
            key = key_for(event)
            if key:
                groups[key].append(event)

    items: list[AnalyticsRankingItem] = []
    for key, rows in groups.items():
        sample = rows[0]
        items.append(AnalyticsRankingItem(
            key=key,
            label=label_for(sample),
            users=len({row.user_id for row in rows}),
            count=len(rows),
            active_seconds=sum(row.active_seconds for row in rows),
            last_active_at=max(_as_utc(row.occurred_at) for row in rows),
            vendor=sample.vendor,
            chip=sample.chip,
            benchmark_name=sample.benchmark_name,
            benchmark_type=sample.benchmark_type,
            test_target=sample.test_target,
        ))
    return sorted(items, key=lambda item: (item.count, item.users), reverse=True)[:limit]


def _simulation_dimensions(
    db: Session, start_at: datetime, end_at: datetime
) -> list[AnalyticsSimulationDimensionItem]:
    tasks = list(db.scalars(
        select(SimulationTask).where(
            SimulationTask.submit_time >= start_at,
            SimulationTask.submit_time <= end_at,
        )
    ).all())
    groups: dict[tuple[str, str, str], list[SimulationTask]] = defaultdict(list)
    for task in tasks:
        groups[(
            task.chip_variant or "默认芯片",
            task.simulator_version,
            task.simulation_mode.value,
        )].append(task)

    results: list[AnalyticsSimulationDimensionItem] = []
    for (chip_variant, simulator_version, simulation_mode), rows in groups.items():
        completed = sum(task.status == TaskStatus.COMPLETED for task in rows)
        terminal = sum(task.status in {
            TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.TERMINATED
        } for task in rows)
        results.append(AnalyticsSimulationDimensionItem(
            key=f"{chip_variant}|{simulator_version}|{simulation_mode}",
            label=f"{chip_variant} / {simulator_version} / {simulation_mode}",
            users=len({task.owner_id for task in rows}),
            tasks=len(rows),
            success_rate=round(completed / terminal * 100, 1) if terminal else 0.0,
            simulator_version=simulator_version,
            chip_variant=chip_variant,
            simulation_mode=simulation_mode,
        ))
    return sorted(results, key=lambda item: item.tasks, reverse=True)[:10]


def get_overview(db: Session, days: int) -> AnalyticsOverviewResponse:
    start_at, end_at = _range(days)
    events = _events_in_range(db, start_at, end_at)
    page_views = [event for event in events if event.event_name == "page_view"]
    duration_events = [event for event in events if event.event_name == "page_active_time"]
    task_count, demand_feedback = _business_counts(db, start_at, end_at)

    day_groups: dict[object, list[AnalyticsEvent]] = defaultdict(list)
    for event in page_views:
        day_groups[_as_utc(event.occurred_at).astimezone(SHANGHAI).date()].append(event)
    trend: list[AnalyticsTrendPoint] = []
    start_day = start_at.astimezone(SHANGHAI).date()
    end_day = end_at.astimezone(SHANGHAI).date()
    cursor = start_day
    while cursor <= end_day:
        rows = day_groups.get(cursor, [])
        trend.append(AnalyticsTrendPoint(
            date=cursor,
            active_users=len({row.user_id for row in rows}),
            visits=len({row.session_id for row in rows}),
            page_views=len(rows),
        ))
        cursor += timedelta(days=1)

    page_duration = Counter()
    for event in duration_events:
        page_duration[event.page_key] += event.active_seconds
    pages = _ranking(
        page_views,
        key_for=lambda event: event.page_key,
        label_for=lambda event: PAGE_LABELS.get(event.page_key, event.page_key or "未知页面"),
        include=lambda event: bool(event.page_key),
    )
    for item in pages:
        item.active_seconds = page_duration[item.key]

    features = _ranking(
        events,
        key_for=lambda event: event.event_name,
        label_for=lambda event: EVENT_LABELS.get(event.event_name, event.event_name),
        include=lambda event: event.event_name in FEATURE_EVENTS,
    )
    chips = _ranking(
        page_views,
        key_for=lambda event: f"{event.vendor or ''}|{event.chip or ''}",
        label_for=lambda event: " / ".join(value for value in (event.vendor, event.chip) if value),
        include=lambda event: bool(event.chip),
    )
    benchmarks = _ranking(
        page_views,
        key_for=lambda event: f"{event.vendor or ''}|{event.chip or ''}|{event.benchmark_name or ''}",
        label_for=lambda event: event.benchmark_name or "",
        include=lambda event: bool(event.benchmark_name),
    )
    benchmark_metadata = {
        f"{event.vendor or ''}|{event.chip or ''}|{event.benchmark_name or ''}": event
        for event in events
        if event.event_name == "benchmark.detail_view" and event.benchmark_name
    }
    for item in benchmarks:
        metadata = benchmark_metadata.get(item.key)
        if metadata is not None:
            item.benchmark_type = metadata.benchmark_type
            item.test_target = metadata.test_target

    return AnalyticsOverviewResponse(
        start_at=start_at,
        end_at=end_at,
        summary=AnalyticsSummary(
            active_users=len({event.user_id for event in page_views}),
            visits=len({event.session_id for event in page_views}),
            page_views=len(page_views),
            active_seconds=sum(event.active_seconds for event in duration_events),
            simulation_tasks=task_count,
            demand_feedback=demand_feedback,
        ),
        trend=trend,
        pages=pages,
        features=features,
        chips=chips,
        benchmarks=benchmarks,
        simulation_dimensions=_simulation_dimensions(db, start_at, end_at),
    )


def _top(counter: Counter[str]) -> str | None:
    return counter.most_common(1)[0][0] if counter else None


def _build_user_items(
    db: Session, events: list[AnalyticsEvent], start_at: datetime, end_at: datetime
) -> list[AnalyticsUserItem]:
    users = {user.id: user for user in db.scalars(select(User)).all()}
    by_user: dict[str, list[AnalyticsEvent]] = defaultdict(list)
    for event in events:
        by_user[event.user_id].append(event)

    task_counts = Counter(dict(db.execute(
        select(SimulationTask.owner_id, func.count()).where(
            SimulationTask.submit_time >= start_at, SimulationTask.submit_time <= end_at
        ).group_by(SimulationTask.owner_id)
    ).all()))
    demand_counts = Counter(dict(db.execute(
        select(User.employee_id, func.count()).join(Demand, Demand.user_id == User.id).where(
            Demand.created_at >= start_at, Demand.created_at <= end_at
        ).group_by(User.employee_id)
    ).all()))
    feedback_counts = Counter(dict(db.execute(
        select(User.employee_id, func.count()).join(FeedbackEntry, FeedbackEntry.user_id == User.id).where(
            FeedbackEntry.created_at >= start_at, FeedbackEntry.created_at <= end_at
        ).group_by(User.employee_id)
    ).all()))

    items: list[AnalyticsUserItem] = []
    for internal_id, rows in by_user.items():
        user = users.get(internal_id)
        if user is None:
            continue
        page_views = [row for row in rows if row.event_name == "page_view"]
        duration_rows = [row for row in rows if row.event_name == "page_active_time"]
        page_counter = Counter(row.page_key for row in page_views if row.page_key)
        chip_counter = Counter(row.chip for row in page_views if row.chip)
        benchmark_counter = Counter(row.benchmark_name for row in page_views if row.benchmark_name)
        items.append(AnalyticsUserItem(
            user_id=user.employee_id,
            display_name=user.display_name,
            role=user.role,
            last_active_at=max((_as_utc(row.occurred_at) for row in rows), default=None),
            active_days=len({_as_utc(row.occurred_at).astimezone(SHANGHAI).date() for row in page_views}),
            visits=len({row.session_id for row in page_views}),
            page_views=len(page_views),
            active_seconds=sum(row.active_seconds for row in duration_rows),
            simulation_tasks=int(task_counts[user.employee_id]),
            demand_feedback=int(demand_counts[user.employee_id] + feedback_counts[user.employee_id]),
            top_page=PAGE_LABELS.get(_top(page_counter) or "", _top(page_counter)),
            top_chip=_top(chip_counter),
            top_benchmark=_top(benchmark_counter),
        ))
    return items


def list_users(
    db: Session,
    *,
    days: int,
    search: str,
    sort_by: str,
    sort_order: str,
    page: int,
    page_size: int,
) -> AnalyticsUserListResponse:
    start_at, end_at = _range(days)
    events = _events_in_range(db, start_at, end_at)
    items = _build_user_items(db, events, start_at, end_at)
    normalized = search.strip().casefold()
    if normalized:
        items = [item for item in items if normalized in item.user_id.casefold() or normalized in item.display_name.casefold()]

    def sort_value(item: AnalyticsUserItem):
        value = getattr(item, sort_by)
        if isinstance(value, datetime):
            return value.timestamp()
        return value or 0

    items.sort(key=sort_value, reverse=sort_order == "desc")
    total = len(items)
    offset = (page - 1) * page_size
    return AnalyticsUserListResponse(
        items=items[offset:offset + page_size], total=total, page=page, page_size=page_size
    )


def get_user_detail(db: Session, employee_id: str, days: int) -> AnalyticsUserDetailResponse | None:
    user = db.scalar(select(User).where(User.employee_id == employee_id))
    if user is None:
        return None
    start_at, end_at = _range(days)
    events = list(db.scalars(
        select(AnalyticsEvent).where(
            AnalyticsEvent.user_id == user.id,
            AnalyticsEvent.occurred_at >= start_at,
            AnalyticsEvent.occurred_at <= end_at,
        ).order_by(AnalyticsEvent.occurred_at.desc())
    ).all())
    items = _build_user_items(db, events, start_at, end_at)
    if not items:
        return None

    page_views = [event for event in events if event.event_name == "page_view"]
    durations = Counter()
    for event in events:
        if event.event_name == "page_active_time":
            durations[event.page_key] += event.active_seconds
    page_groups: dict[str, list[AnalyticsEvent]] = defaultdict(list)
    for event in page_views:
        page_groups[event.page_key].append(event)
    pages = sorted([
        AnalyticsUserPageItem(
            page_key=key,
            label=PAGE_LABELS.get(key, key),
            page_views=len(rows),
            active_seconds=durations[key],
            last_active_at=max(_as_utc(row.occurred_at) for row in rows),
        )
        for key, rows in page_groups.items()
    ], key=lambda item: item.page_views, reverse=True)
    recent_events = [
        AnalyticsUserEventItem(
            event_name=event.event_name,
            label=EVENT_LABELS.get(event.event_name, event.event_name),
            page_key=event.page_key,
            occurred_at=_as_utc(event.occurred_at),
            vendor=event.vendor,
            chip=event.chip,
            benchmark_name=event.benchmark_name,
            simulator_version=event.simulator_version,
            chip_variant=event.chip_variant,
        )
        for event in events if event.event_name != "page_active_time"
    ][:30]
    return AnalyticsUserDetailResponse(user=items[0], pages=pages, recent_events=recent_events)
