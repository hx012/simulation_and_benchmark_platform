"""Create a completed local task fixture for frontend development."""

import argparse
import json
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.common.config import get_settings
from app.common.database import SessionLocal
from app.simulation.enums import (
    ExecutionPhase,
    SimulationMode,
    TaskStatus,
    TraceStatus,
)
from app.simulation.models import SimulationTask


DEFAULT_TASK_ID = "SIM-20260818-024736-A3051FC3"
TOTAL_CYCLE = 2_004_642
RUNTIME_SECONDS = 5.589225732721388
LOG_LINE_COUNT = 10_000

SUBMIT_TIME = datetime.fromisoformat("2026-08-18T02:47:36.200604+00:00")
START_TIME = datetime.fromisoformat("2026-08-18T02:47:36.494280+00:00")
END_TIME = datetime.fromisoformat("2026-08-18T02:47:42.156402+00:00")
GENERATED_AT = datetime.fromisoformat("2026-08-18T02:47:42.159551+00:00")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed a completed simulation task for local UI development."
    )
    parser.add_argument("--trace-source", required=True, type=Path)
    parser.add_argument("--task-id", default=DEFAULT_TASK_ID)
    parser.add_argument("--task-name", default="V310 API E2E")
    parser.add_argument("--owner-id", default="test-user")
    return parser.parse_args()


def validate_task_id(task_id: str) -> None:
    if not task_id.startswith("SIM-") or any(
        character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        for character in task_id
    ):
        raise ValueError(f"Invalid task ID: {task_id}")


def validate_trace(source: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Trace source does not exist: {source}")

    with source.open("r", encoding="utf-8") as file:
        trace = json.load(file)

    if not isinstance(trace, list):
        raise ValueError("Trace JSON root must be an array")
    if any(not isinstance(event, dict) for event in trace):
        raise ValueError("Every trace event must be an object")


def write_log(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8", newline="\n") as file:
        for line_number in range(1, LOG_LINE_COUNT + 1):
            progress = (line_number - 1) / (LOG_LINE_COUNT - 1)
            cycle = round(TOTAL_CYCLE * progress)
            timestamp = START_TIME + timedelta(
                seconds=RUNTIME_SECONDS * progress
            )

            if line_number == 1:
                message = "simulator started; initializing V310 single-chip runtime"
            elif line_number == LOG_LINE_COUNT:
                message = "simulation completed successfully; exit_code=0"
            elif line_number % 1000 == 0:
                message = (
                    f"progress checkpoint; completed={progress:.1%}; "
                    "collecting performance counters"
                )
            else:
                core_id = (line_number - 1) % 8
                instruction_count = 96 + (line_number % 160)
                message = (
                    f"AICore[{core_id}] executed instruction batch; "
                    f"instructions={instruction_count}"
                )

            file.write(
                f"{timestamp.isoformat()} [INFO] "
                f"line={line_number:05d} cycle={cycle:07d} {message}\n"
            )


def write_summary(
    summary_path: Path,
    *,
    task_id: str,
    task_name: str,
    owner_id: str,
) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": "1.0",
        "task": {
            "task_id": task_id,
            "task_name": task_name,
            "owner_id": owner_id,
            "rerun_from_task_id": None,
        },
        "simulator": {
            "version": "v310",
            "chip_variant": None,
            "simulation_mode": "SINGLE_CHIP",
        },
        "result": {
            "status": "COMPLETED",
            "current_cycle": TOTAL_CYCLE,
            "total_cycle": TOTAL_CYCLE,
            "simulated_time_seconds": 2.00464e-06,
            "runtime_seconds": RUNTIME_SECONDS,
            "exit_code": 0,
            "trace_status": "READY",
            "trace_path": "result/trace/dumps/trace.json",
            "error_code": None,
            "error_message": None,
        },
        "time": {
            "submit_time": SUBMIT_TIME.isoformat(),
            "start_time": START_TIME.isoformat(),
            "end_time": END_TIME.isoformat(),
            "generated_at": GENERATED_AT.isoformat(),
        },
    }

    with summary_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
        file.write("\n")


def upsert_task(
    workspace: Path,
    *,
    task_id: str,
    task_name: str,
    owner_id: str,
) -> None:
    values = {
        "task_name": task_name,
        "owner_id": owner_id,
        "simulator_version": "v310",
        "chip_variant": None,
        "simulation_mode": SimulationMode.SINGLE_CHIP,
        "rerun_from_task_id": None,
        "status": TaskStatus.COMPLETED,
        "execution_phase": ExecutionPhase.FINISHED,
        "worker_id": "local-worker-01",
        "claimed_at": START_TIME,
        "pid": None,
        "pgid": None,
        "exit_code": 0,
        "current_cycle": TOTAL_CYCLE,
        "log_read_offset": 0,
        "cancel_requested": False,
        "terminate_requested": False,
        "workspace_path": str(workspace),
        "total_cycle": TOTAL_CYCLE,
        "runtime_seconds": RUNTIME_SECONDS,
        "simulated_time_seconds": 2.00464e-06,
        "trace_status": TraceStatus.READY,
        "error_code": None,
        "error_message": None,
        "submit_time": SUBMIT_TIME,
        "start_time": START_TIME,
        "end_time": END_TIME,
        "archived": False,
        "archived_at": None,
    }

    with SessionLocal() as db:
        task = db.scalar(
            select(SimulationTask).where(SimulationTask.task_id == task_id)
        )
        if task is None:
            task = SimulationTask(task_id=task_id, **values)
            db.add(task)
        else:
            for field, value in values.items():
                setattr(task, field, value)
        db.commit()


def main() -> None:
    args = parse_args()
    validate_task_id(args.task_id)

    trace_source = args.trace_source.expanduser().resolve()
    validate_trace(trace_source)

    settings = get_settings()
    task_root = Path(settings.task_root).resolve()
    workspace = (task_root / args.task_id).resolve()
    workspace.relative_to(task_root)

    trace_path = workspace / "result" / "trace" / "dumps" / "trace.json"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(trace_source, trace_path)

    write_log(workspace / "logs" / "davinci_sim.log")
    write_summary(
        workspace / "result" / "summary.json",
        task_id=args.task_id,
        task_name=args.task_name,
        owner_id=args.owner_id,
    )
    upsert_task(
        workspace,
        task_id=args.task_id,
        task_name=args.task_name,
        owner_id=args.owner_id,
    )

    print(f"task_id: {args.task_id}")
    print(f"workspace: {workspace}")
    print(f"log_lines: {LOG_LINE_COUNT}")
    print(f"trace_source: {trace_source}")
    print("database: upserted")


if __name__ == "__main__":
    main()
