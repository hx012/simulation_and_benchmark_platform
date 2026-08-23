import json
from dataclasses import dataclass
from pathlib import Path

from app.common.config import Settings
from app.simulation.exceptions import TaskIOError
from app.simulation.models import SimulationTask


@dataclass(frozen=True)
class LogChunk:
    available: bool
    offset: int
    next_offset: int
    eof: bool
    reset: bool
    text: str


@dataclass(frozen=True)
class ResultArtifacts:
    trace_available: bool
    trace_source_available: bool
    trace_viewer_available: bool
    summary_available: bool
    summary: dict | None
    summary_error: str | None


class SimulationTaskIOService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.task_root = Path(settings.task_root).resolve()

    def read_log(
        self,
        task: SimulationTask,
        *,
        offset: int,
        limit_bytes: int,
    ) -> LogChunk:
        if offset < 0:
            raise TaskIOError("Log offset must be >= 0")

        if limit_bytes <= 0:
            raise TaskIOError("Log limit_bytes must be > 0")

        if limit_bytes > self.settings.sim_log_max_chunk_bytes:
            raise TaskIOError(
                "Log limit_bytes exceeds maximum: "
                f"{self.settings.sim_log_max_chunk_bytes}"
            )

        workspace = self._workspace(task)
        log_path = workspace / "logs" / "davinci_sim.log"

        if not log_path.is_file():
            return LogChunk(
                available=False,
                offset=offset,
                next_offset=offset,
                eof=True,
                reset=False,
                text="",
            )

        file_size = log_path.stat().st_size
        actual_offset = offset
        reset = False

        if actual_offset > file_size:
            actual_offset = 0
            reset = True

        with log_path.open("rb") as file:
            file.seek(actual_offset)
            data = file.read(limit_bytes)
            next_offset = file.tell()

        text = data.decode(
            "utf-8",
            errors="replace",
        )

        return LogChunk(
            available=True,
            offset=actual_offset,
            next_offset=next_offset,
            eof=next_offset >= file_size,
            reset=reset,
            text=text,
        )

    def read_result_artifacts(
        self,
        task: SimulationTask,
    ) -> ResultArtifacts:
        workspace = self._workspace(task)

        summary_path = workspace / "result" / "summary.json"
        trace_path = (
            workspace
            / "result"
            / "trace"
            / "dumps"
            / "trace.json"
        )
        trace_viewer_path = workspace / "result" / "trace" / "trace.html"

        summary: dict | None = None
        summary_error: str | None = None

        if summary_path.is_file():
            try:
                with summary_path.open(
                    "r",
                    encoding="utf-8",
                ) as file:
                    loaded = json.load(file)

                if isinstance(loaded, dict):
                    summary = loaded
                else:
                    summary_error = (
                        "summary.json root is not an object"
                    )
            except Exception as exc:
                summary_error = str(exc)

        return ResultArtifacts(
            trace_available=trace_path.is_file(),
            trace_source_available=trace_path.is_file(),
            trace_viewer_available=trace_viewer_path.is_file(),
            summary_available=summary_path.is_file(),
            summary=summary,
            summary_error=summary_error,
        )


    def read_trace_events(
        self,
        task: SimulationTask,
    ) -> list[dict]:
        workspace = self._workspace(task)
        trace_path = (
            workspace
            / "result"
            / "trace"
            / "dumps"
            / "trace.json"
        )

        if not trace_path.is_file():
            raise TaskIOError("Trace is not available for this task")

        size = trace_path.stat().st_size
        if size > self.settings.sim_trace_max_bytes:
            raise TaskIOError(
                "Trace file exceeds API size limit: "
                f"{size} bytes"
            )

        try:
            with trace_path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
        except Exception as exc:
            raise TaskIOError(
                f"Unable to read trace.json: {exc}"
            ) from exc

        if not isinstance(loaded, list):
            raise TaskIOError("trace.json root must be an array")

        events: list[dict] = []
        for index, item in enumerate(loaded):
            if not isinstance(item, dict):
                raise TaskIOError(
                    f"trace.json event {index} is not an object"
                )
            events.append(item)

        return events

    def get_trace_viewer_path(
        self,
        task: SimulationTask,
    ) -> Path:
        workspace = self._workspace(task)
        trace_viewer_path = workspace / "result" / "trace" / "trace.html"

        if not trace_viewer_path.is_file():
            raise TaskIOError("Catapult Trace Viewer is not available for this task")

        try:
            resolved_viewer_path = trace_viewer_path.resolve(strict=True)
            resolved_viewer_path.relative_to(workspace)
        except (OSError, ValueError) as exc:
            raise TaskIOError(
                "Trace Viewer artifact is outside task workspace"
            ) from exc

        return resolved_viewer_path

    def _workspace(
        self,
        task: SimulationTask,
    ) -> Path:
        workspace = Path(task.workspace_path).resolve()

        try:
            workspace.relative_to(self.task_root)
        except ValueError as exc:
            raise TaskIOError(
                "Task workspace is outside TASK_ROOT"
            ) from exc

        return workspace
