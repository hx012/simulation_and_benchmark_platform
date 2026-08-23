from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CommunityLink(BaseModel):
    key: str
    name: str
    url: str
    enabled: bool


class PlatformConfigResponse(BaseModel):
    communities: list[CommunityLink]


class TeamAchievement(BaseModel):
    title: str
    category: str = "团队成果"
    summary: str = ""
    contributors: str = ""
    date: str = ""


class TeamConfigResponse(BaseModel):
    name: str
    description: str
    specialties: list[str]
    achievements: list[TeamAchievement]


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
    created_at: datetime


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
    support_count: int
    voted_by_me: bool
    is_own: bool
    created_at: datetime
    updated_at: datetime


class DemandListResponse(BaseModel):
    items: list[DemandResponse]
    total: int


class DemandVoteResponse(BaseModel):
    demand_id: str
    support_count: int
    voted_by_me: bool
