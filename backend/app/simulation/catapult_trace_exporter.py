from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.common.config import BACKEND_ROOT, Settings


@dataclass(frozen=True)
class CatapultTraceExportResult:
    success: bool
    trace_html_path: Path | None
    exit_code: int
    error_message: str | None = None


class CatapultTraceExporter:
    ALLOWED_CONFIGS = {"chrome", "full", "lean", "systrace", "v8"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.task_root = Path(settings.task_root).resolve()
        self.adapter_script = (
            BACKEND_ROOT / "scripts" / "catapult_trace2html.py"
        )

    def run(
        self,
        workspace_path: str,
        *,
        title: str,
    ) -> CatapultTraceExportResult:
        try:
            workspace = Path(workspace_path).resolve()
            workspace.relative_to(self.task_root)
        except ValueError:
            return self._failure("Task workspace is outside TASK_ROOT")

        trace_root = (workspace / "result" / "trace").resolve()
        trace_json_path = trace_root / "dumps" / "trace.json"
        trace_html_path = trace_root / "trace.html"
        temp_html_path = trace_root / "trace.html.tmp"
        log_root = (workspace / "logs").resolve()
        log_path = log_root / "catapult_trace2html.log"
        catapult_home = Path(self.settings.catapult_home).resolve()
        catapult_entry = (
            catapult_home / "tracing" / "tracing_build" / "trace2html.py"
        )

        if not trace_json_path.is_file():
            return self._failure(f"Trace source not found: {trace_json_path}")

        try:
            trace_root.relative_to(workspace)
            log_root.relative_to(workspace)
            trace_json_path = trace_json_path.resolve(strict=True)
            trace_json_path.relative_to(workspace)
        except (OSError, ValueError):
            return self._failure(
                "Catapult input or output path is outside task workspace"
            )

        source_size = trace_json_path.stat().st_size
        if source_size > self.settings.sim_trace_max_bytes:
            return self._failure(
                "Trace source exceeds viewer size limit: "
                f"{source_size} bytes"
            )

        if not catapult_entry.is_file():
            return self._failure(
                f"Catapult trace2html not found: {catapult_entry}"
            )

        if not self.adapter_script.is_file():
            return self._failure(
                f"Catapult adapter not found: {self.adapter_script}"
            )

        config_name = self.settings.sim_trace_viewer_config.strip().lower()
        if config_name not in self.ALLOWED_CONFIGS:
            return self._failure(
                "Unsupported Catapult viewer config: "
                f"{self.settings.sim_trace_viewer_config}"
            )

        trace_root.mkdir(parents=True, exist_ok=True)
        log_root.mkdir(parents=True, exist_ok=True)
        temp_html_path.unlink(missing_ok=True)

        python_executable = (
            Path(self.settings.catapult_python).resolve()
            if self.settings.catapult_python
            else Path(sys.executable).resolve()
        )
        command = [
            str(python_executable),
            str(self.adapter_script),
            "--catapult-root",
            str(catapult_home),
            "--input",
            str(trace_json_path),
            "--output",
            str(temp_html_path),
            "--config",
            config_name,
            "--title",
            title,
        ]

        try:
            with log_path.open("w", encoding="utf-8") as log_file:
                process = subprocess.run(
                    command,
                    cwd=BACKEND_ROOT,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=self.settings.sim_trace_viewer_timeout_seconds,
                )
        except subprocess.TimeoutExpired:
            temp_html_path.unlink(missing_ok=True)
            return self._failure(
                "Catapult trace2html timed out after "
                f"{self.settings.sim_trace_viewer_timeout_seconds:g} seconds",
                exit_code=-1,
            )
        except OSError as exc:
            temp_html_path.unlink(missing_ok=True)
            return self._failure(
                f"Unable to start Catapult trace2html: {exc}",
                exit_code=-1,
            )

        if process.returncode != 0:
            temp_html_path.unlink(missing_ok=True)
            return self._failure(
                "Catapult trace2html exited with code "
                f"{process.returncode}; see {log_path}",
                exit_code=process.returncode,
            )

        if not temp_html_path.is_file() or temp_html_path.stat().st_size == 0:
            temp_html_path.unlink(missing_ok=True)
            return self._failure(
                "Catapult trace2html completed without a viewer artifact",
                exit_code=process.returncode,
            )

        output_size = temp_html_path.stat().st_size
        if output_size > self.settings.sim_trace_viewer_max_output_bytes:
            temp_html_path.unlink(missing_ok=True)
            return self._failure(
                "Catapult viewer exceeds output size limit: "
                f"{output_size} bytes",
                exit_code=process.returncode,
            )

        temp_html_path.replace(trace_html_path)
        return CatapultTraceExportResult(
            success=True,
            trace_html_path=trace_html_path,
            exit_code=process.returncode,
        )

    @staticmethod
    def _failure(
        message: str,
        *,
        exit_code: int = -1,
    ) -> CatapultTraceExportResult:
        return CatapultTraceExportResult(
            success=False,
            trace_html_path=None,
            exit_code=exit_code,
            error_message=message,
        )
