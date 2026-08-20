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
            return TraceResult(
                success=False,
                trace_path=None,
                exit_code=-1,
                error_message=(
                    "SIMULATOR_HOME is not configured"
                ),
            )

        simulator_home = simulator_home.resolve()

        trace_script = (
                simulator_home
                / "v310_deployment"
                / "script"
                / "trace_generator.py"
        )

        if not trace_script.is_file():
            return TraceResult(
                success=False,
                trace_path=None,
                exit_code=-1,
                error_message=(
                    f"Trace generator not found: "
                    f"{trace_script}"
                ),
            )

        workspace = Path(
            workspace_path
        ).resolve()

        trace_root = (
                workspace
                / "result"
                / "trace"
        )

        dump_dir = (
                trace_root
                / "dumps"
        )

        trace_log = (
                workspace
                / "logs"
                / "trace_generator.log"
        )

        trace_path = (
                dump_dir
                / "trace.json"
        )

        if not dump_dir.is_dir():
            return TraceResult(
                success=False,
                trace_path=None,
                exit_code=-1,
                error_message=(
                    f"Dump directory does not exist: "
                    f"{dump_dir}"
                ),
            )

        trace_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        trace_log.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        env = os.environ.copy()

        # 保持和 Simulator 一样能够 import
        # DavinciSimulator Python 模块。
        old_pythonpath = env.get("PYTHONPATH")

        if old_pythonpath:
            env["PYTHONPATH"] = (
                    str(simulator_home)
                    + os.pathsep
                    + old_pythonpath
            )
        else:
            env["PYTHONPATH"] = str(
                simulator_home
            )

        command = [
            sys.executable,
            str(trace_script),
        ]

        with trace_log.open(
                "w"
        ) as log_file:
            process = subprocess.run(
                command,
                cwd=trace_root,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=False,
            )

        if process.returncode != 0:
            return TraceResult(
                success=False,
                trace_path=None,
                exit_code=process.returncode,
                error_message=(
                    "Trace generator exited "
                    f"with code {process.returncode}"
                ),
            )

        if not trace_path.is_file():
            return TraceResult(
                success=False,
                trace_path=None,
                exit_code=process.returncode,
                error_message=(
                    "Trace generator completed "
                    "but trace.json was not created"
                ),
            )

        return TraceResult(
            success=True,
            trace_path=trace_path,
            exit_code=process.returncode,
        )