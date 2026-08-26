from chip_performance_analysis import TraceTimeResult

from app.performance.schemas import (
    TraceTimeAnalysisResponse,
    TraceTimeItemResponse,
)


def trace_time_response(
    result: TraceTimeResult,
    *,
    source: str,
    source_name: str,
    task_id: str | None = None,
) -> TraceTimeAnalysisResponse:
    return TraceTimeAnalysisResponse(
        source=source,
        source_name=source_name,
        task_id=task_id,
        producer=result.producer,
        unit=result.unit,
        event_count=result.event_count,
        analyzed_event_count=result.analyzed_event_count,
        skipped_event_count=result.skipped_event_count,
        sync_event_count=result.sync_event_count,
        total_cycles=result.total_cycles,
        items=[
            TraceTimeItemResponse(
                name=item.name,
                cycles=item.cycles,
                ratio_percent=item.ratio_percent,
            )
            for item in result.items
        ],
        warnings=result.warnings,
    )
