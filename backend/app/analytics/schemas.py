from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnalyticsEventCreate(BaseModel):
    event_id: str = Field(min_length=8, max_length=64)
    session_id: str = Field(min_length=8, max_length=64)
    event_name: str = Field(min_length=2, max_length=128)
    page_key: str = Field(default="", max_length=128)
    result: str = Field(default="", max_length=32)
    active_seconds: int = Field(default=0, ge=0, le=86_400)
    vendor: str | None = Field(default=None, max_length=128)
    chip: str | None = Field(default=None, max_length=128)
    benchmark_name: str | None = Field(default=None, max_length=255)
    benchmark_type: str | None = Field(default=None, max_length=64)
    test_target: str | None = Field(default=None, max_length=128)
    simulator_version: str | None = Field(default=None, max_length=128)
    chip_variant: str | None = Field(default=None, max_length=128)
    simulation_mode: str | None = Field(default=None, max_length=64)
    target_type: str | None = Field(default=None, max_length=64)
    target_id: str | None = Field(default=None, max_length=512)
    target_name: str | None = Field(default=None, max_length=255)

    @field_validator(
        "page_key", "result", "vendor", "chip", "benchmark_name", "benchmark_type",
        "test_target", "simulator_version", "chip_variant", "simulation_mode",
        "target_type", "target_id", "target_name",
    )
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class AnalyticsEventAccepted(BaseModel):
    accepted: bool = True


class AnalyticsSummary(BaseModel):
    active_users: int
    visits: int
    page_views: int
    active_seconds: int
    simulation_tasks: int
    demand_feedback: int


class AnalyticsTrendPoint(BaseModel):
    date: date
    active_users: int
    visits: int
    page_views: int


class AnalyticsRankingItem(BaseModel):
    key: str
    label: str
    users: int
    count: int
    active_seconds: int = 0
    last_active_at: datetime | None = None
    vendor: str | None = None
    chip: str | None = None
    benchmark_name: str | None = None
    benchmark_type: str | None = None
    test_target: str | None = None


class AnalyticsSimulationDimensionItem(BaseModel):
    key: str
    label: str
    users: int
    tasks: int
    success_rate: float
    simulator_version: str | None = None
    chip_variant: str | None = None
    simulation_mode: str | None = None


class AnalyticsOverviewResponse(BaseModel):
    start_at: datetime
    end_at: datetime
    summary: AnalyticsSummary
    trend: list[AnalyticsTrendPoint]
    pages: list[AnalyticsRankingItem]
    features: list[AnalyticsRankingItem]
    chips: list[AnalyticsRankingItem]
    benchmarks: list[AnalyticsRankingItem]
    simulation_dimensions: list[AnalyticsSimulationDimensionItem]


AnalyticsUserSort = Literal[
    "last_active_at", "active_days", "visits", "page_views", "active_seconds",
    "simulation_tasks", "demand_feedback",
]


class AnalyticsUserItem(BaseModel):
    user_id: str
    display_name: str
    role: str
    last_active_at: datetime | None
    active_days: int
    visits: int
    page_views: int
    active_seconds: int
    simulation_tasks: int
    demand_feedback: int
    top_page: str | None
    top_chip: str | None
    top_benchmark: str | None


class AnalyticsUserListResponse(BaseModel):
    items: list[AnalyticsUserItem]
    total: int
    page: int
    page_size: int


class AnalyticsUserPageItem(BaseModel):
    page_key: str
    label: str
    page_views: int
    active_seconds: int
    last_active_at: datetime | None


class AnalyticsUserEventItem(BaseModel):
    event_name: str
    label: str
    page_key: str
    occurred_at: datetime
    vendor: str | None = None
    chip: str | None = None
    benchmark_name: str | None = None
    simulator_version: str | None = None
    chip_variant: str | None = None


class AnalyticsUserDetailResponse(BaseModel):
    user: AnalyticsUserItem
    pages: list[AnalyticsUserPageItem]
    recent_events: list[AnalyticsUserEventItem]
