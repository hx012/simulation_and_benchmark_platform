import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.common.config import Settings


@dataclass(frozen=True)
class TraceResult:
    success: bool
    trace_path: Path | None
    viewer_path: Path | None
    exit_code: int
    error_message: str | None = None


class TraceRunner:
    def __init__(
            self,
            settings: Settings,
    ) -> None:
        self.settings = settings

    def run(
            self,
            workspace_path: str,
    ) -> TraceResult:
        simulator_home = self.settings.simulator_home

        if simulator_home is None:
            return TraceResult(False, None, None, -1, "SIMULATOR_HOME is not configured")

        simulator_home = simulator_home.resolve()
        trace_script = simulator_home / "v310_deployment" / "script" / "trace_generator.py"

        if not trace_script.is_file():
            return TraceResult(False, None, None, -1, f"Trace generator not found: {trace_script}")

        workspace = Path(workspace_path).resolve()
        trace_root = workspace / "result" / "trace"
        dump_dir = trace_root / "dumps"
        trace_log = workspace / "logs" / "trace_generator.log"
        trace_path = dump_dir / "trace.json"
        viewer_path = trace_root / "trace.html"

        if not dump_dir.is_dir():
            return TraceResult(False, None, None, -1, f"Dump directory does not exist: {dump_dir}")

        trace_root.mkdir(parents=True, exist_ok=True)
        trace_log.parent.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        old_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(simulator_home) + (os.pathsep + old_pythonpath if old_pythonpath else "")

        with trace_log.open("w") as log_file:
            process = subprocess.run(
                [sys.executable, str(trace_script)],
                cwd=trace_root,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=False,
            )

        if process.returncode != 0 or not trace_path.is_file():
            return TraceResult(False, None, None, process.returncode, "Trace generation failed")

        trace2html = self.settings.trace2html_path
        if trace2html and Path(trace2html).is_file():
            html_process = subprocess.run(
                [str(trace2html), str(trace_path), "--output", str(viewer_path)],
                cwd=trace_root,
                check=False,
            )
            if html_process.returncode != 0:
                viewer_path = None

        return TraceResult(
            success=True,
            trace_path=trace_path,
            viewer_path=viewer_path if viewer_path and viewer_path.is_file() else None,
            exit_code=process.returncode,
        )
