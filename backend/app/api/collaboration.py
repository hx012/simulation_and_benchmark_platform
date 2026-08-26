from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.service import AuthenticatedUser, get_current_user, require_admin
from app.collaboration.content import community_links, load_team_config, platform_support
from app.collaboration.schemas import (
    DemandCreate,
    DemandListResponse,
    DemandResponse,
    DemandVoteResponse,
    FeedbackCreate,
    FeedbackResponse,
    PlatformConfigResponse,
    TeamConfigResponse,
)
from app.collaboration.service import (
    create_demand,
    create_feedback,
    demand_response,
    get_visible_demand,
    list_demands,
    list_feedback,
    set_vote,
)
from app.common.config import Settings, get_settings
from app.common.database import get_db


router = APIRouter(prefix="/api", tags=["collaboration"])


@router.get("/platform-config", response_model=PlatformConfigResponse)
def platform_config(
    settings: Settings = Depends(get_settings),
) -> PlatformConfigResponse:
    return PlatformConfigResponse(
        communities=community_links(settings),
        support=platform_support(settings),
    )


@router.get("/team", response_model=TeamConfigResponse)
def team_config(
    _: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> TeamConfigResponse:
    return load_team_config(settings)


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(get_current_user),
) -> FeedbackResponse:
    return create_feedback(db, current, payload)


@router.get("/admin/feedback", response_model=list[FeedbackResponse])
def admin_feedback(
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_admin),
) -> list[FeedbackResponse]:
    return list_feedback(db)


@router.get("/demands", response_model=DemandListResponse)
def demands(
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DemandListResponse:
    items = list_demands(db, current, settings)
    return DemandListResponse(items=items, total=len(items))


@router.post("/demands", response_model=DemandResponse, status_code=status.HTTP_201_CREATED)
def submit_demand(
    payload: DemandCreate,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DemandResponse:
    item = create_demand(db, current, payload)
    return demand_response(db, item, current.user, current, settings)


@router.put("/demands/{demand_id}/vote", response_model=DemandVoteResponse)
def vote_demand(
    demand_id: str,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DemandVoteResponse:
    item, _ = get_visible_demand(db, demand_id, current, settings)
    return set_vote(db, item, current, True)


@router.delete("/demands/{demand_id}/vote", response_model=DemandVoteResponse)
def unvote_demand(
    demand_id: str,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DemandVoteResponse:
    item, _ = get_visible_demand(db, demand_id, current, settings)
    return set_vote(db, item, current, False)
