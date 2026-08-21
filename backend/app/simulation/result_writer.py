import json
from datetime import datetime, timezone
from pathlib import Path

from app.simulation.enums import TraceStatus
from app.simulation.models import SimulationTask


class ResultWriter:
    def write_summary(
        self,
        task: SimulationTask,
    ) -> Path:
        workspace = Path(task.workspace_path).resolve()
        result_dir = workspace / "result"
        result_dir.mkdir(parents=True, exist_ok=True)

        summary_path = result_dir / "summary.json"
        trace_path = workspace / "result" / "trace" / "dumps" / "trace.json"
        trace_viewer_path = workspace / "result" / "trace" / "trace.html"

        summary = {
            "schema_version": "1.0",
            "task": {
                "task_id": task.task_id,
                "task_name": task.task_name,
                "owner_id": task.owner_id,
                "rerun_from_task_id": task.rerun_from_task_id,
            },
            "simulator": {
                "version": task.simulator_version,
                "chip_variant": task.chip_variant,
                "simulation_mode": task.simulation_mode.value,
            },
            "result": {
                "status": task.status.value,
                "current_cycle": task.current_cycle,
                "total_cycle": task.total_cycle,
                "simulated_time_seconds": task.simulated_time_seconds,
                "runtime_seconds": task.runtime_seconds,
                "exit_code": task.exit_code,
                "trace_status": task.trace_status.value,
                "trace_path": (
                    str(trace_path.relative_to(workspace))
                    if task.trace_status == TraceStatus.READY and trace_path.is_file()
                    else None
                ),
                "trace_viewer_path": (
                    str(trace_viewer_path.relative_to(workspace))
                    if task.trace_status == TraceStatus.READY and trace_viewer_path.is_file()
                    else None
                ),
                "error_code": task.error_code,
                "error_message": task.error_message,
            },
            "time": {
                "submit_time": task.submit_time.isoformat() if task.submit_time else None,
                "start_time": task.start_time.isoformat() if task.start_time else None,
                "end_time": task.end_time.isoformat() if task.end_time else None,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        temp_path = summary_path.with_suffix(".json.tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(summary, file, ensure_ascii=False, indent=2)

        temp_path.replace(summary_path)
        return summary_path
