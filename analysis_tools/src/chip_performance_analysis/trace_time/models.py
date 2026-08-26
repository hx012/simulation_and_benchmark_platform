from dataclasses import dataclass, field
from enum import Enum


class TraceProducer(str, Enum):
    MSKPP = "mskpp"
    ESL = "esl"


class TraceAnalysisError(ValueError):
    """Raised when trace data does not match the selected producer."""


@dataclass(frozen=True)
class TraceTimeItem:
    name: str
    cycles: float
    ratio_percent: float


@dataclass(frozen=True)
class TraceTimeResult:
    producer: TraceProducer
    unit: str
    event_count: int
    analyzed_event_count: int
    skipped_event_count: int
    sync_event_count: int
    total_cycles: float
    items: list[TraceTimeItem]
    warnings: list[str] = field(default_factory=list)
