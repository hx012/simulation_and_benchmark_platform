from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import AuthenticatedUser, get_current_user
from app.common.config import Settings, get_settings
from app.common.database import get_db
from app.recent_activity.schemas import RecentActivityListResponse
from app.recent_activity.service import list_recent_activities


router = APIRouter(prefix="/api/recent-activities", tags=["recent-activities"])


@router.get("", response_model=RecentActivityListResponse)
def recent_activities(
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> RecentActivityListResponse:
    return list_recent_activities(db, current, settings)
