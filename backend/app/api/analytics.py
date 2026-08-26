from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.analytics.schemas import (
    AnalyticsEventAccepted,
    AnalyticsEventCreate,
    AnalyticsOverviewResponse,
    AnalyticsUserDetailResponse,
    AnalyticsUserListResponse,
    AnalyticsUserSort,
)
from app.analytics.service import create_event, get_overview, get_user_detail, list_users
from app.auth.service import AuthenticatedUser, get_current_user, require_admin
from app.common.database import get_db


router = APIRouter(prefix="/api", tags=["analytics"])


@router.post(
    "/analytics/events",
    response_model=AnalyticsEventAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def collect_event(
    payload: AnalyticsEventCreate,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(get_current_user),
) -> AnalyticsEventAccepted:
    create_event(db, current.user, payload)
    return AnalyticsEventAccepted()


@router.get("/admin/analytics/overview", response_model=AnalyticsOverviewResponse)
def analytics_overview(
    days: int = Query(default=30, ge=1, le=366),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_admin),
) -> AnalyticsOverviewResponse:
    return get_overview(db, days)


@router.get("/admin/analytics/users", response_model=AnalyticsUserListResponse)
def analytics_users(
    days: int = Query(default=30, ge=1, le=366),
    search: str = Query(default="", max_length=128),
    sort_by: AnalyticsUserSort = Query(default="last_active_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_admin),
) -> AnalyticsUserListResponse:
    return list_users(
        db, days=days, search=search, sort_by=sort_by, sort_order=sort_order,
        page=page, page_size=page_size,
    )


@router.get(
    "/admin/analytics/users/{employee_id}",
    response_model=AnalyticsUserDetailResponse,
)
def analytics_user_detail(
    employee_id: str,
    days: int = Query(default=30, ge=1, le=366),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_admin),
) -> AnalyticsUserDetailResponse:
    result = get_user_detail(db, employee_id, days)
    if result is None:
        raise HTTPException(status_code=404, detail="所选时间范围内没有该用户的行为数据")
    return result
