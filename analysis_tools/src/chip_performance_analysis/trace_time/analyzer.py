import math
from collections.abc import Mapping, Sequence
from typing import Any

from .models import (
    TraceAnalysisError,
    TraceProducer,
    TraceTimeItem,
    TraceTimeResult,
)


SYNC_NAMES = {
    "WAIT_FLAG", "SET_FLAG", "HSET_FLAG", "HWAIT_FLAG", "flow", "BAR",
    "setFlag", "waitFlag", "flowCtrlBarSet", "flowCtrlBarWait",
    "flowCtrlSetFlag", "flowCtrlWaitFlag", "flowCtrlBar",
    "flowCtrlHsetFlag", "flowCtrlHwaitFlag", "flowCtrlHsetFlagXt",
    "flowCtrlHwaitFlagXt", "flowCtrlWaitFlagDev", "flowCtrlWaitFlagDevI",
    "flowCtrlSetCrossCore", "flowCtrlSetIntraBlock",
    "flowCtrlWaitIntraBlock", "flowCtrlGetBuf", "flowCtrlRlsBuf",
    "vectorSetFlagV", "vectorWaitFlagV", "vectorGetBufV", "vectorRlsBufV",
    "vectorSetIntraBlockV", "vectorWaitIntraBlockV", "vectorSetCrossCoreV",
    "vectorWaitFlagDevV", "vectorWaitFlagDeviV",
}

ESL_CYCLE_SCALE = 1.65
ESL_TIME_SCALE = 1000


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    converted = float(value)
    return converted if math.isfinite(converted) else None


def _merge_intervals(intervals: list[tuple[float, float]]) -> float:
    if not intervals:
        return 0.0
    intervals.sort(key=lambda item: item[0])
    current_start, duration = intervals[0]
    current_end = current_start + duration
    total = 0.0
    for start, next_duration in intervals[1:]:
        end = start + next_duration
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end
    return total + current_end - current_start


def normalize_trace_json(json_data: Any) -> list[dict[str, Any]]:
    if isinstance(json_data, list):
        raw_events = json_data
    elif isinstance(json_data, Mapping):
        raw_events = json_data.get("traceEvents")
        if not isinstance(raw_events, list):
            raise TraceAnalysisError(
                "Trace object must contain a traceEvents array"
            )
    else:
        raise TraceAnalysisError(
            "Trace root must be an array or an object containing traceEvents"
        )

    events: list[dict[str, Any]] = []
    for index, event in enumerate(raw_events):
        if not isinstance(event, Mapping):
            raise TraceAnalysisError(f"Trace event {index} is not an object")
        events.append(dict(event))
    return events


def analyze_trace(
    events: Sequence[Mapping[str, Any]],
    producer: TraceProducer | str,
) -> TraceTimeResult:
    try:
        selected = TraceProducer(producer)
    except ValueError as exc:
        raise TraceAnalysisError(f"Unsupported trace producer: {producer}") from exc

    normalized = [
        event if isinstance(event, dict) else dict(event)
        for event in events
    ]
    if not normalized:
        raise TraceAnalysisError("Trace contains no events")
    if selected == TraceProducer.MSKPP:
        return _analyze_mskpp(normalized)
    return _analyze_esl(normalized)


def _result(
    *,
    producer: TraceProducer,
    events: list[dict[str, Any]],
    values: Mapping[str, float],
    analyzed_count: int,
    skipped_count: int,
    sync_count: int,
    total_cycles: float,
    warnings: list[str],
) -> TraceTimeResult:
    denominator = total_cycles if total_cycles > 0 else sum(values.values())
    items = [
        TraceTimeItem(
            name=name,
            cycles=cycles,
            ratio_percent=(cycles / denominator * 100 if denominator else 0.0),
        )
        for name, cycles in sorted(
            values.items(), key=lambda item: item[1], reverse=True
        )
    ]
    return TraceTimeResult(
        producer=producer,
        unit="cycle",
        event_count=len(events),
        analyzed_event_count=analyzed_count,
        skipped_event_count=skipped_count,
        sync_event_count=sync_count,
        total_cycles=total_cycles,
        items=items,
        warnings=warnings,
    )


def _analyze_mskpp(events: list[dict[str, Any]]) -> TraceTimeResult:
    tid_pipe_map: dict[Any, str] = {}
    for event in events:
        tid = event.get("tid")
        args = event.get("args")
        if tid is None or not isinstance(args, Mapping):
            continue
        name = args.get("name")
        if isinstance(name, str) and name.strip() and name != "AICore":
            tid_pipe_map[tid] = name.strip()

    if not tid_pipe_map:
        raise TraceAnalysisError(
            "The selected MSKPP trace has no valid tid-to-pipe mappings in args.name"
        )

    starts = {name: math.inf for name in set(tid_pipe_map.values())}
    grouped: dict[str, dict[Any, list[tuple[float, float]]]] = {
        name: {} for name in starts
    }
    global_start = math.inf
    global_end = -math.inf
    analyzed_count = 0
    skipped_count = 0
    sync_count = 0

    for event in events:
        timestamp = _finite_number(event.get("ts"))
        duration = _finite_number(event.get("dur"))
        pipe_name = tid_pipe_map.get(event.get("tid"))

        if timestamp is not None and pipe_name is not None:
            starts[pipe_name] = min(starts[pipe_name], timestamp)

        if timestamp is None or duration is None or duration < 0:
            skipped_count += 1
            continue

        global_start = min(global_start, timestamp)
        global_end = max(global_end, timestamp + duration)

        if pipe_name is None:
            skipped_count += 1
            continue
        if event.get("name") in SYNC_NAMES:
            sync_count += 1
            continue

        by_tid = grouped[pipe_name].setdefault(event.get("tid"), [])
        by_tid.append((timestamp, duration))
        analyzed_count += 1

    values: dict[str, float] = {}
    for pipe_name, by_tid in grouped.items():
        start = starts[pipe_name]
        if start == math.inf:
            values[pipe_name] = 0.0
            continue
        total = 0.0
        for intervals in by_tid.values():
            adjusted = [
                (math.ceil(timestamp - start), math.ceil(duration))
                for timestamp, duration in intervals
            ]
            total += _merge_intervals(adjusted)
        values[pipe_name] = total

    if not any(value > 0 for value in values.values()):
        raise TraceAnalysisError(
            "The selected MSKPP trace contains no analyzable duration events"
        )

    total_cycles = (
        global_end - global_start
        if global_start != math.inf and global_end != -math.inf
        else 0.0
    )
    warnings = []
    if skipped_count:
        warnings.append(f"Skipped {skipped_count} incomplete or unmapped events")
    return _result(
        producer=TraceProducer.MSKPP,
        events=events,
        values=values,
        analyzed_count=analyzed_count,
        skipped_count=skipped_count,
        sync_count=sync_count,
        total_cycles=total_cycles,
        warnings=warnings,
    )


def _analyze_esl(events: list[dict[str, Any]]) -> TraceTimeResult:
    timestamps = [
        value
        for event in events
        if (value := _finite_number(event.get("ts"))) is not None
    ]
    if not timestamps:
        raise TraceAnalysisError("The selected ESL trace contains no timestamps")
    global_start = min(timestamps)
    global_end = global_start

    grouped: dict[Any, dict[str, dict[str, list[tuple[float, float]]]]] = {}
    analyzed_count = 0
    skipped_count = 0
    sync_count = 0

    for event in events:
        if event.get("name") in SYNC_NAMES:
            sync_count += 1
            continue
        tid = event.get("tid")
        timestamp = _finite_number(event.get("ts"))
        duration = _finite_number(event.get("dur"))
        pid = event.get("pid")
        if (
            tid is None
            or timestamp is None
            or duration is None
            or duration < 0
            or not isinstance(pid, str)
            or "." not in pid
        ):
            skipped_count += 1
            continue

        core, subcore = pid.split(".", 1)
        if not core or not subcore:
            skipped_count += 1
            continue

        global_end = max(global_end, timestamp + duration)
        intervals = (
            grouped.setdefault(tid, {})
            .setdefault(core, {})
            .setdefault(subcore, [])
        )
        intervals.append(
            (
                math.ceil((timestamp - global_start) * ESL_TIME_SCALE),
                math.ceil(duration * ESL_TIME_SCALE),
            )
        )
        analyzed_count += 1

    if not grouped:
        raise TraceAnalysisError(
            "The selected ESL trace has no events with a core.subcore pid"
        )

    values: dict[str, float] = {}
    for tid, by_core in grouped.items():
        total = 0.0
        for by_subcore in by_core.values():
            for intervals in by_subcore.values():
                total += _merge_intervals(intervals)
        values[str(tid)] = total * ESL_CYCLE_SCALE

    total_cycles = (
        (global_end - global_start) * ESL_TIME_SCALE * ESL_CYCLE_SCALE
    )
    warnings = []
    if skipped_count:
        warnings.append(
            f"Skipped {skipped_count} events without ESL core.subcore timing fields"
        )
    return _result(
        producer=TraceProducer.ESL,
        events=events,
        values=values,
        analyzed_count=analyzed_count,
        skipped_count=skipped_count,
        sync_count=sync_count,
        total_cycles=total_cycles,
        warnings=warnings,
    )
