from typing import Literal

from pydantic import BaseModel

from chip_performance_analysis import TraceProducer


class TraceTimeItemResponse(BaseModel):
    name: str
    cycles: float
    ratio_percent: float


class TraceTimeAnalysisResponse(BaseModel):
    data_type: Literal["trace"] = "trace"
    source: Literal["simulation_task", "local_file"]
    source_name: str
    task_id: str | None = None
    producer: TraceProducer
    unit: str
    event_count: int
    analyzed_event_count: int
    skipped_event_count: int
    sync_event_count: int
    total_cycles: float
    items: list[TraceTimeItemResponse]
    warnings: list[str]
