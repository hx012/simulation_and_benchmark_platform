import os
from dataclasses import dataclass
from pathlib import Path

from app.common.config import Settings
from app.simulation.models import SimulationTask
from app.simulation.simulator.profiles import (
    SimulatorProfileRegistry,
)


@dataclass(frozen=True)
class LaunchSpec:
    command: list[str]
    cwd: Path
    env: dict[str, str]

    log_path: Path
    dump_dir: Path


class SimulatorLaunchError(Exception):
    pass


class SimulatorAdapter:
    def __init__(
            self,
            settings: Settings,
            profile_registry: SimulatorProfileRegistry,
    ) -> None:
        self.settings = settings
        self.profile_registry = profile_registry

    def build_launch_spec(self, task: SimulationTask) -> LaunchSpec:
        simulator_home = self.settings.simulator_home
        sst_executable = self.settings.sst_executable

        if simulator_home is None:
            raise SimulatorLaunchError(
                "SIMULATOR_HOME is not configured"
            )

        if sst_executable is None:
            raise SimulatorLaunchError(
                "SST_EXECUTABLE is not configured"
            )

        simulator_home = simulator_home.resolve()
        sst_executable = sst_executable.resolve()

        if not simulator_home.is_dir():
            raise SimulatorLaunchError(
                f"Simulator home does not exist: "
                f"{simulator_home}"
            )

        if not sst_executable.is_file():
            raise SimulatorLaunchError(
                f"SST executable does not exist: "
                f"{sst_executable}"
            )

        profile = self.profile_registry.get_profile(
            simulator_version=task.simulator_version,
            chip_variant=task.chip_variant,
            simulation_mode=task.simulation_mode,
        )

        entry_script = (
                simulator_home / profile.entry_script
        ).resolve()

        # 防止 profile 使用 ../../ 逃出 Simulator 根目录。
        if not entry_script.is_relative_to(simulator_home):
            raise SimulatorLaunchError(
                f"Entry script escapes simulator home: "
                f"{entry_script}"
            )

        if not entry_script.is_file():
            raise SimulatorLaunchError(
                f"Simulator entry script does not exist: "
                f"{entry_script}"
            )

        workspace = Path(task.workspace_path).resolve()
        simulator_config_dir = (
                workspace
                / "input"
                / "chip_config"
                )

        workload_config_dir = (
                workspace
                / "runtime"
                / "resolved_config"
                / "workload"
        )

        if not simulator_config_dir.is_dir():
            raise SimulatorLaunchError(
                f"Simulator config directory does not exist: "
                f"{simulator_config_dir}"
            )

        if not workload_config_dir.is_dir():
            raise SimulatorLaunchError(
                f"Workload config directory does not exist: "
                f"{workload_config_dir}"
            )

        log_path = (
                workspace
                / "logs"
                / "davinci_sim.log"
        )

        dump_dir = (
                workspace
                / "result"
                / "trace"
                / "dumps"
        )

        command = [
            str(sst_executable),
            *profile.sst_args,
            str(entry_script),
        ]

        env = os.environ.copy()

        env["DAVINCI_SIM_ROOT"] = str(
            simulator_home
        )

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

        env["DAVINCI_DUMP_DIR"] = str(
            dump_dir
        )

        env["DAVINCI_SIMULATOR_CONFIG_DIR"] = str(
            simulator_config_dir
                )

        env["DAVINCI_WORKLOAD_CONFIG_DIR"] = str(
            workload_config_dir
        )

        return LaunchSpec(
            command=command,
            cwd=simulator_home,
            env=env,
            log_path=log_path,
            dump_dir=dump_dir,
        )