from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.constants import DEMAND_VIEW_RESOURCE, TEAM_VIEW_RESOURCE
from app.auth.service import AuthenticatedUser, get_current_user, require_admin, require_resource
from app.collaboration.content import community_links, load_feature_releases, load_team_config, platform_support
from app.collaboration.schemas import (
    DemandCreate,
    DemandAdminUpdate,
    DemandListResponse,
    DemandResponse,
    DemandUpdate,
    DemandVoteResponse,
    FeedbackAdminUpdate,
    FeedbackCreate,
    FeedbackMessageCreate,
    FeedbackResponse,
    FeatureReleaseConfigResponse,
    PlatformConfigResponse,
    TeamConfigResponse,
    TeamAchievementCreate,
    TeamAchievementResponse,
    TeamAchievementScoreUpdate,
    TeamAchievementUpdate,
)
from app.collaboration.team_service import (
    create_achievement,
    delete_achievement,
    enrich_team_members,
    list_achievements,
    score_achievement,
    update_achievement,
)
from app.collaboration.service import (
    add_feedback_message,
    create_demand,
    create_feedback,
    demand_response,
    get_visible_demand,
    list_demands,
    list_feedback,
    list_my_feedback,
    review_demand,
    review_feedback,
    set_vote,
    update_demand,
    withdraw_demand,
    withdraw_feedback,
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
    current: AuthenticatedUser = Depends(require_resource(TEAM_VIEW_RESOURCE)),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TeamConfigResponse:
    team = load_team_config(settings)
    enrich_team_members(db, current, team)
    return team


@router.get("/team/avatars/{filename}")
def team_avatar(
    filename: str,
    _: AuthenticatedUser = Depends(require_resource(TEAM_VIEW_RESOURCE)),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    normalized = Path(filename).name
    if normalized != filename or Path(normalized).suffix.lower() not in {".webp", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=404, detail="头像不存在")
    root = (settings.platform_team_avatar_dir or settings.platform_content_config.parent / "team-avatars").resolve()
    target = (root / normalized).resolve()
    if target.parent != root or not target.is_file():
        raise HTTPException(status_code=404, detail="头像不存在")
    return FileResponse(target)


@router.get("/team/achievement-archives/{employee_id}", response_model=list[TeamAchievementResponse])
def team_achievement_archive(
    employee_id: str,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_resource(TEAM_VIEW_RESOURCE)),
    settings: Settings = Depends(get_settings),
) -> list[TeamAchievementResponse]:
    visibility = load_team_config(settings).archive_visibility
    return list_achievements(db, current, employee_id, visibility)


@router.post("/team/achievement-archives", response_model=TeamAchievementResponse, status_code=status.HTTP_201_CREATED)
def add_team_achievement(
    payload: TeamAchievementCreate,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_resource(TEAM_VIEW_RESOURCE)),
) -> TeamAchievementResponse:
    return create_achievement(db, current, payload)


@router.patch("/team/achievement-archives/{achievement_id}", response_model=TeamAchievementResponse)
def edit_team_achievement(
    achievement_id: str,
    payload: TeamAchievementUpdate,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_resource(TEAM_VIEW_RESOURCE)),
) -> TeamAchievementResponse:
    return update_achievement(db, current, achievement_id, payload)


@router.delete("/team/achievement-archives/{achievement_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_achievement(
    achievement_id: str,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_resource(TEAM_VIEW_RESOURCE)),
) -> None:
    delete_achievement(db, current, achievement_id)


@router.patch("/admin/team/achievement-archives/{achievement_id}/score", response_model=TeamAchievementResponse)
def rate_team_achievement(
    achievement_id: str,
    payload: TeamAchievementScoreUpdate,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_admin),
) -> TeamAchievementResponse:
    return score_achievement(db, current, achievement_id, payload.score)


@router.get("/feature-releases", response_model=FeatureReleaseConfigResponse)
def feature_releases(
    _: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> FeatureReleaseConfigResponse:
    return load_feature_releases(settings)


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(get_current_user),
) -> FeedbackResponse:
    return create_feedback(db, current, payload)


@router.get("/feedback/mine", response_model=list[FeedbackResponse])
def my_feedback(
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(get_current_user),
) -> list[FeedbackResponse]:
    return list_my_feedback(db, current)


@router.post("/feedback/{feedback_id}/messages", response_model=FeedbackResponse)
def supplement_feedback(
    feedback_id: str,
    payload: FeedbackMessageCreate,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(get_current_user),
) -> FeedbackResponse:
    return add_feedback_message(db, feedback_id, current, payload.content)


@router.post("/feedback/{feedback_id}/withdraw", response_model=FeedbackResponse)
def cancel_feedback(
    feedback_id: str,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(get_current_user),
) -> FeedbackResponse:
    return withdraw_feedback(db, feedback_id, current)


@router.get("/admin/feedback", response_model=list[FeedbackResponse])
def admin_feedback(
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_admin),
) -> list[FeedbackResponse]:
    return list_feedback(db, current)


@router.patch("/admin/feedback/{feedback_id}", response_model=FeedbackResponse)
def handle_feedback(
    feedback_id: str,
    payload: FeedbackAdminUpdate,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_admin),
) -> FeedbackResponse:
    return review_feedback(db, feedback_id, current, payload)


@router.get("/demands", response_model=DemandListResponse)
def demands(
    scope: str = "public",
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_resource(DEMAND_VIEW_RESOURCE)),
) -> DemandListResponse:
    items = list_demands(db, current, scope)
    return DemandListResponse(items=items, total=len(items))


@router.post("/demands", response_model=DemandResponse, status_code=status.HTTP_201_CREATED)
def submit_demand(
    payload: DemandCreate,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_resource(DEMAND_VIEW_RESOURCE)),
) -> DemandResponse:
    item = create_demand(db, current, payload)
    return demand_response(db, item, current.user, current)


@router.patch("/demands/{demand_id}", response_model=DemandResponse)
def edit_demand(
    demand_id: str,
    payload: DemandUpdate,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_resource(DEMAND_VIEW_RESOURCE)),
) -> DemandResponse:
    return update_demand(db, demand_id, current, payload)


@router.post("/demands/{demand_id}/withdraw", response_model=DemandResponse)
def cancel_demand(
    demand_id: str,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_resource(DEMAND_VIEW_RESOURCE)),
) -> DemandResponse:
    return withdraw_demand(db, demand_id, current)


@router.get("/admin/demands", response_model=DemandListResponse)
def admin_demands(
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_admin),
) -> DemandListResponse:
    items = list_demands(db, current, "all")
    return DemandListResponse(items=items, total=len(items))


@router.patch("/admin/demands/{demand_id}", response_model=DemandResponse)
def handle_demand(
    demand_id: str,
    payload: DemandAdminUpdate,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_admin),
) -> DemandResponse:
    return review_demand(db, demand_id, current, payload)


@router.put("/demands/{demand_id}/vote", response_model=DemandVoteResponse)
def vote_demand(
    demand_id: str,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_resource(DEMAND_VIEW_RESOURCE)),
) -> DemandVoteResponse:
    item, _ = get_visible_demand(db, demand_id, current)
    return set_vote(db, item, current, True)


@router.delete("/demands/{demand_id}/vote", response_model=DemandVoteResponse)
def unvote_demand(
    demand_id: str,
    db: Session = Depends(get_db),
    current: AuthenticatedUser = Depends(require_resource(DEMAND_VIEW_RESOURCE)),
) -> DemandVoteResponse:
    item, _ = get_visible_demand(db, demand_id, current)
    return set_vote(db, item, current, False)
