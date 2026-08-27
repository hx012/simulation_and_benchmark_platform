from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CommunityLink(BaseModel):
    key: str
    name: str
    url: str
    enabled: bool
    group: Literal["ecosystem", "support"] = "ecosystem"
    order: int = 0


class PlatformSupport(BaseModel):
    key: str = "mskpp_support"
    name: str = "MSKPP 技术支撑群"
    resource: str = "welink_support_group"
    enabled: bool = True


class PlatformConfigResponse(BaseModel):
    communities: list[CommunityLink]
    support: PlatformSupport = Field(default_factory=PlatformSupport)


class TeamAchievement(BaseModel):
    id: str = ""
    title: str
    category: str = "团队成果"
    summary: str = ""
    contributors: str = ""
    date: str = ""
    featured: bool = False
    featured_order: int = 0
    enabled: bool = True
    detail_url: str = ""


class TeamMember(BaseModel):
    employee_id: str
    name: str
    direction: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    order: int = 0
    enabled: bool = True


class TeamContribution(BaseModel):
    member: str
    contribution: str = ""
    achievement_count: int = 0
    contribution_score: int = 0
    views: int = 0


class TeamConfigResponse(BaseModel):
    name: str
    description: str
    team_size: str = ""
    specialties: list[str] = Field(default_factory=list)
    members: list[TeamMember] = Field(default_factory=list)
    achievements: list[TeamAchievement] = Field(default_factory=list)
    contributions: list[TeamContribution] = Field(default_factory=list)
    all_achievements_url: str = ""


class FeedbackCreate(BaseModel):
    feedback_type: Literal["experience", "function", "data", "other"] = "experience"
    page_title: str = Field(default="", max_length=255)
    page_path: str = Field(default="", max_length=512)
    content: str = Field(min_length=2, max_length=5000)


class FeedbackResponse(BaseModel):
    feedback_id: str
    user_id: str
    display_name: str
    feedback_type: str
    page_title: str
    page_path: str
    content: str
    status: str
    resolution: str
    handler_name: str = ""
    messages: list["FeedbackMessageResponse"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    can_withdraw: bool = False
    can_reply: bool = False


class FeedbackMessageCreate(BaseModel):
    content: str = Field(min_length=2, max_length=5000)


class FeedbackMessageResponse(BaseModel):
    message_id: str
    author_name: str
    author_role: str
    content: str
    created_at: datetime


class FeedbackAdminUpdate(BaseModel):
    status: Literal["pending", "processing", "needs_info", "resolved", "closed"]
    resolution: str = Field(default="", max_length=5000)
    reply: str = Field(default="", max_length=5000)


class DemandCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    domain: str = Field(min_length=1, max_length=64)
    expected_time: str = Field(default="", max_length=64)
    background: str = Field(min_length=2, max_length=10000)
    description: str = Field(min_length=2, max_length=10000)
    business_value: str = Field(min_length=2, max_length=10000)
    contact: str = Field(default="", max_length=255)


class DemandResponse(BaseModel):
    demand_id: str
    request_no: str
    submitter_id: str
    submitter_name: str
    title: str
    domain: str
    expected_time: str
    background: str
    description: str
    business_value: str
    contact: str
    status: str
    conclusion: str
    visibility: str
    priority: str
    planned_time: str
    handler_name: str = ""
    support_count: int
    voted_by_me: bool
    is_own: bool
    created_at: datetime
    updated_at: datetime
    can_edit: bool = False
    can_withdraw: bool = False
    history: list["DemandEventResponse"] = Field(default_factory=list)


class DemandListResponse(BaseModel):
    items: list[DemandResponse]
    total: int


class DemandVoteResponse(BaseModel):
    demand_id: str
    support_count: int
    voted_by_me: bool


class DemandUpdate(DemandCreate):
    pass


class DemandAdminUpdate(BaseModel):
    status: Literal[
        "pending", "needs_info", "accepted", "planned", "in_progress",
        "delivered", "deferred", "rejected",
    ]
    conclusion: str = Field(default="", max_length=10000)
    visibility: Literal["private", "public"] = "private"
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    planned_time: str = Field(default="", max_length=64)


class DemandEventResponse(BaseModel):
    event_id: str
    actor_name: str
    actor_role: str
    event_type: str
    from_status: str
    to_status: str
    comment: str
    created_at: datetime
