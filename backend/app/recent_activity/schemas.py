from datetime import datetime
from string import Formatter

from pydantic import BaseModel, ConfigDict, Field, model_validator


TEMPLATE_FIELDS = {
    "event_name", "page_key", "result", "active_seconds", "vendor", "chip",
    "benchmark_name", "benchmark_type", "test_target", "simulator_version",
    "chip_variant", "simulation_mode", "target_type", "target_id", "target_name",
    "relative_time",
}


class RecentActivityHomeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    storage_limit: int = Field(default=5, ge=1, le=100)
    display_limit: int = Field(default=3, ge=1, le=20)
    title: str = "近期工作"
    description: str = "当前用户最近访问和操作"
    empty_text: str = "暂无近期工作"

    @model_validator(mode="after")
    def validate_limits(self) -> "RecentActivityHomeConfig":
        if self.display_limit > self.storage_limit:
            raise ValueError("recent activity display_limit cannot exceed storage_limit")
        return self


class RecentActivityEventConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    domain: str = Field(min_length=1, max_length=64)
    icon: str = Field(default="", max_length=16)
    title_template: str = Field(min_length=1, max_length=512)
    description_template: str = Field(min_length=1, max_length=512)
    action_label: str = Field(min_length=1, max_length=64)
    route: str = Field(min_length=1, max_length=1024)
    dedupe_key: str = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def validate_internal_route(self) -> "RecentActivityEventConfig":
        if not self.route.startswith("/") or self.route.startswith("//"):
            raise ValueError("recent activity routes must be internal absolute paths")
        for template in (
            self.title_template, self.description_template, self.route, self.dedupe_key
        ):
            for _, field_name, format_spec, conversion in Formatter().parse(template):
                if format_spec or conversion:
                    raise ValueError("recent activity templates do not support format specifications")
                if field_name is not None and field_name not in TEMPLATE_FIELDS:
                    raise ValueError(f"unsupported recent activity template field: {field_name}")
        return self


class RecentActivityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    home: RecentActivityHomeConfig = Field(default_factory=RecentActivityHomeConfig)
    events: dict[str, RecentActivityEventConfig] = Field(default_factory=dict)


class RecentActivityItem(BaseModel):
    id: str
    event_name: str
    domain: str
    icon: str
    title: str
    description: str
    action_label: str
    href: str
    occurred_at: datetime


class RecentActivityListResponse(BaseModel):
    title: str
    description: str
    empty_text: str
    items: list[RecentActivityItem]
