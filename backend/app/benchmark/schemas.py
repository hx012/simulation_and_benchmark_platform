from typing import Any

from pydantic import BaseModel, Field


class BenchmarkStatusResponse(BaseModel):
    registry_available: bool
    results_available: bool


class ChipSummary(BaseModel):
    vendor: str
    chip: str


class ChipListResponse(BaseModel):
    items: list[ChipSummary]
    total: int


class ChipDetail(ChipSummary):
    benchmark_dir: str
    benchmark_registry: str
    benchmark_count: int


class BenchmarkDefinition(BaseModel):
    benchmark_id: str
    vendor: str
    chip: str
    name: str
    module: str
    class_name: str
    description: str = ""

    # Current registries do not require these fields.  They are intentionally
    # optional so a future registry schema can add them without breaking V0.1.
    category: str | None = None
    target: str | None = None


class BenchmarkListResponse(BaseModel):
    vendor: str
    chip: str
    items: list[BenchmarkDefinition]
    total: int


class BenchmarkResultListResponse(BaseModel):
    vendor: str
    chip: str
    benchmark_name: str
    configured: bool
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
