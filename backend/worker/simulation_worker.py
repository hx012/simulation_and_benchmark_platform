import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from app.analytics.service import delete_expired_events
from app.common.config import get_settings
from app.common.database import SessionLocal
from app.simulation.enums import TaskStatus
from app.simulation.repository import SimulationRepository
from app.simulation.task_service import SimulationTaskService
from app.simulation.simulator.adapter import (
    LaunchSpec,
    SimulatorAdapter,
)
from app.simulation.simulator.profiles import (
    SimulatorProfileRegistry,
)
from app.simulation.workload_resolver import (
    WorkloadConfigResolver,
)
from app.simulation.simulator.cycle_parser import (
    CycleParser,
)
from app.simulation.simulator.trace_runner import (
    TraceRunner,
)
from app.simulation.catapult_trace_exporter import (
    CatapultTraceExporter,
)
from app.simulation.result_writer import (
    ResultWriter,
)
from app.simulation.simulator.result_parser import (
    SimulationResultParser,
)

@dataclass
class RunningTask:
    task_id: str
    process: subprocess.Popen
    pgid: int
    start_monotonic: float
    log_path: Path
    last_progress_update: float


class SimulationWorker:
    def __init__(self) -> None:
        self.settings = get_settings()

        self.repository = SimulationRepository()

        self.task_service = SimulationTaskService(
            self.repository
        )

        self.profile_registry = SimulatorProfileRegistry(
            self.settings.simulator_profiles_file
        )

        self.simulator_adapter = SimulatorAdapter(
            settings=self.settings,
            profile_registry=self.profile_registry,
        )

        self.workload_resolver = (
            WorkloadConfigResolver()
        )

        self.cycle_parser = CycleParser()

        self.worker_id = self.settings.sim_worker_id

        self.max_concurrent_tasks = (
            self.settings.sim_max_concurrent_tasks
        )

        self.poll_interval = (
            self.settings.sim_worker_poll_interval_seconds
        )

        self.progress_update_interval = (
            self.settings.sim_progress_update_interval_seconds
        )

        self.terminate_grace_seconds = (
            self.settings.sim_terminate_grace_seconds
        )

        self.recovery_grace_seconds = (
            self.settings.sim_worker_recovery_grace_seconds
        )

        self.analytics_cleanup_interval_seconds = (
            self.settings.analytics_cleanup_interval_hours * 60 * 60
        )
        self._next_analytics_cleanup_at = 0.0

        self.trace_runner = TraceRunner(
            settings=self.settings,
        )
        self.trace_exporter = CatapultTraceExporter(
            settings=self.settings,
        )
        self.result_writer = ResultWriter()

        self.result_parser = SimulationResultParser()

        self.running_tasks: dict[str, RunningTask] = {}

    def run(self, until_idle: bool = False) -> None:
        print(
            f"[worker] started "
            f"worker_id={self.worker_id} "
            f"max_concurrent={self.max_concurrent_tasks}"
        )

        self._recover_owned_tasks()

        try:
            while True:
                self._cleanup_expired_analytics_events_if_due()
                self._poll_running_tasks()

                made_progress = self._fill_available_slots()

                if (
                    until_idle
                    and not self.running_tasks
                    and not made_progress
                ):
                    print("[worker] queue idle, exiting")
                    return

                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\n[worker] interrupted")
            self._shutdown_running_tasks()

    def _cleanup_expired_analytics_events_if_due(self) -> None:
        now = time.monotonic()
        if now < self._next_analytics_cleanup_at:
            return

        self._next_analytics_cleanup_at = now + self.analytics_cleanup_interval_seconds
        retention_days = self.settings.analytics_event_retention_days
        if retention_days == 0:
            return

        try:
            with SessionLocal.begin() as db:
                deleted = delete_expired_events(db, retention_days)
            if deleted:
                print(
                    f"[worker] analytics cleanup deleted={deleted} "
                    f"retention_days={retention_days}"
                )
        except SQLAlchemyError as error:
            retry_seconds = min(self.analytics_cleanup_interval_seconds, 300.0)
            self._next_analytics_cleanup_at = now + retry_seconds
            print(
                f"[worker] analytics cleanup failed: {error}",
                file=sys.stderr,
            )

    def _fill_available_slots(self) -> bool:
        made_progress = False

        while (
            len(self.running_tasks)
            < self.max_concurrent_tasks
        ):
            handled = self._claim_and_launch_one()

            if not handled:
                break

            made_progress = True

        return made_progress

    def _claim_and_launch_one(self) -> bool:
        # 1. FIFO claim
        with SessionLocal.begin() as db:
            task = self.repository.claim_next_queued_task(
                db,
                worker_id=self.worker_id,
            )

            if task is None:
                return False

            task_id = task.task_id
            workspace_path = task.workspace_path

        print(f"[worker] claimed {task_id}")

        # 2. 准备 workspace
        try:
            self._prepare_workspace(
                workspace_path
            )
        except Exception as exc:
            self._mark_failed(
                task_id,
                "WORKSPACE_PREPARE_FAILED",
                str(exc),
            )
            return True

        try:
            with SessionLocal() as db:
                task = self.repository.get_task(
                    db,
                    task_id,
                )

                if task is None:
                    raise RuntimeError(
                        f"Task disappeared: {task_id}"
                    )

                self._prepare_task_input(
                    task
                )

        except Exception as exc:
            self._mark_failed(
                task_id,
                "INPUT_PREPARE_FAILED",
                str(exc),
            )
            return True


        # 3. 真正启动前最后检查 cancel_requested
        try:
            with SessionLocal.begin() as db:
                can_start = self.task_service.prepare_start(
                    db,
                    task_id,
                    self.worker_id,
                )

            if not can_start:
                print(
                    f"[worker] cancelled before launch "
                    f"{task_id}"
                )
                self._write_summary(task_id)
                return True

        except Exception as exc:
            self._mark_failed(
                task_id,
                "PREPARE_START_FAILED",
                str(exc),
            )
            return True

        # 4. 根据任务类型构造 LaunchSpec 并启动 Simulator
        process = None
        pgid = None

        try:
            with SessionLocal() as db:
                task = self.repository.get_task(
                    db,
                    task_id,
                )

                if task is None:
                    raise RuntimeError(
                        f"Task disappeared: {task_id}"
                    )

                launch_spec = self._build_launch_spec(
                    task
                )

            launch_spec.log_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            launch_spec.dump_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            with launch_spec.log_path.open(
                    "a"
            ) as log_file:
                process = subprocess.Popen(
                    launch_spec.command,
                    cwd=launch_spec.cwd,
                    env=launch_spec.env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )

            pgid = os.getpgid(process.pid)

            with SessionLocal.begin() as db:
                self.task_service.mark_running(
                    db,
                    task_id,
                    self.worker_id,
                    pid=process.pid,
                    pgid=pgid,
                )

            self.running_tasks[task_id] = RunningTask(
                task_id=task_id,
                process=process,
                pgid=pgid,
                start_monotonic=time.monotonic(),
                log_path=launch_spec.log_path,
                last_progress_update=0.0,
            )

            print(
                f"[worker] running {task_id} "
                f"pid={process.pid} "
                f"pgid={pgid}"
            )

            return True

        except Exception as exc:
            if (
                    process is not None
                    and process.poll() is None
                    and pgid is not None
            ):
                try:
                    os.killpg(
                        pgid,
                        signal.SIGKILL,
                    )
                except ProcessLookupError:
                    pass

            self._mark_failed(
                task_id,
                "SIM_START_FAILED",
                str(exc),
            )

            return True

    def _poll_running_tasks(self) -> None:
        for task_id, running in list(
            self.running_tasks.items()
        ):
            now = time.monotonic()
            if (
                now - running.last_progress_update
                >= self.progress_update_interval
            ):
                try:
                    self._update_task_progress(running)
                except Exception as exc:
                    print(
                        f"[worker] progress update failed "
                        f"for {task_id}: {exc}"
                    )
                running.last_progress_update = now
            # 先检查是否收到 terminate 请求
            if self._is_terminate_requested(task_id):
                self._terminate_task(running)
                del self.running_tasks[task_id]
                continue

            return_code = running.process.poll()

            if return_code is None:
                continue

            # Simulator 已退出。
            # 无论是否到 3 秒更新周期，都强制读取一次剩余日志，
            # 确保最终 SST Cycle 写入数据库。
            try:
                self._update_task_progress(
                    running
                )
            except Exception as exc:
                print(
                    f"[worker] final progress update failed "
                    f"for {task_id}: {exc}"
                )

            runtime_seconds = (
                    time.monotonic()
                    - running.start_monotonic
            )

            print(
                f"[worker] process exited "
                f"{task_id} "
                f"exit_code={return_code}"
            )

            if return_code == 0:
                try:
                    with SessionLocal.begin() as db:
                        self.task_service.mark_collecting(
                            db,
                            task_id,
                            exit_code=return_code,
                        )

                    with SessionLocal() as db:
                        task = self.repository.get_task(
                            db,
                            task_id,
                        )

                        if task is None:
                            raise RuntimeError(
                                f"Task disappeared: {task_id}"
                            )

                        simulator_version = (
                            task.simulator_version
                        )

                        workspace_path = (
                            task.workspace_path
                        )

                    # 真实 Simulator 生成 Trace。
                    if simulator_version != "mock":
                        self._generate_trace(
                            task_id,
                            workspace_path,
                        )

                    # final progress flush 已经在前面执行过。
                    with SessionLocal() as db:
                        task = self.repository.get_task(
                            db,
                            task_id,
                        )

                        if task is None:
                            raise RuntimeError(
                                f"Task disappeared: {task_id}"
                            )

                        final_cycle = task.current_cycle

                    simulated_time_seconds = (
                        self.result_parser
                        .parse_simulated_time_from_file(
                            running.log_path
                        )
                    )

                    with SessionLocal.begin() as db:
                        self.task_service.mark_completed(
                            db,
                            task_id,
                            total_cycle=final_cycle,
                            simulated_time_seconds=(
                                simulated_time_seconds
                            ),
                            runtime_seconds=runtime_seconds,
                        )
                        print(
                            f"[worker] simulation result "
                            f"{task_id}: "
                            f"total_cycle={final_cycle}, "
                            f"simulated_time_seconds="
                            f"{simulated_time_seconds}, "
                            f"runtime_seconds={runtime_seconds:.3f}"
                        )

                    # COMPLETED 已经落库以后再生成 summary。
                    self._write_summary(
                        task_id
                    )

                    print(
                        f"[worker] completed {task_id}"
                    )

                except Exception as exc:
                    self._mark_failed(
                        task_id,
                        "RESULT_COLLECT_FAILED",
                        str(exc),
                        exit_code=return_code,
                    )
            else:
                self._mark_failed(
                    task_id,
                    "SIM_PROCESS_FAILED",
                    (
                        f"Simulator process exited "
                        f"with code {return_code}"
                    ),
                    exit_code=return_code,
                )

            del self.running_tasks[task_id]

    def _is_terminate_requested(
        self,
        task_id: str,
    ) -> bool:
        with SessionLocal() as db:
            task = self.repository.get_task(
                db,
                task_id,
            )

            if task is None:
                return False

            return (
                task.status == TaskStatus.RUNNING
                and task.terminate_requested
            )

    def _terminate_task(
        self,
        running: RunningTask,
    ) -> None:
        task_id = running.task_id

        print(
            f"[worker] terminating {task_id} "
            f"pgid={running.pgid}"
        )

        try:
            os.killpg(
                running.pgid,
                signal.SIGTERM,
            )
        except ProcessLookupError:
            pass

        try:
            return_code = running.process.wait(
                timeout=self.terminate_grace_seconds
            )
        except subprocess.TimeoutExpired:
            print(
                f"[worker] SIGTERM timeout, "
                f"sending SIGKILL {task_id}"
            )

            try:
                os.killpg(
                    running.pgid,
                    signal.SIGKILL,
                )
            except ProcessLookupError:
                pass

            return_code = running.process.wait()

        try:
            self._update_task_progress(
                running
            )
        except Exception as exc:
            print(
                f"[worker] final progress update failed "
                f"for {task_id}: {exc}"
            )
        with SessionLocal.begin() as db:
            self.task_service.mark_terminated(
                db,
                task_id,
                exit_code=return_code,
            )

        self._write_summary(task_id)

        print(
            f"[worker] terminated {task_id} "
            f"exit_code={return_code}"
        )

    def _recover_owned_tasks(self) -> None:
        with SessionLocal() as db:
            tasks = self.repository.list_worker_owned_incomplete_tasks(
                db,
                self.worker_id,
            )
            snapshots = [
                (
                    task.task_id,
                    task.status,
                    task.pgid,
                    task.terminate_requested,
                )
                for task in tasks
            ]

        if not snapshots:
            return

        print(
            f"[worker] recovering {len(snapshots)} "
            f"task(s) owned by {self.worker_id}"
        )

        for (
            task_id,
            status,
            pgid,
            terminate_requested,
        ) in snapshots:
            if status == TaskStatus.QUEUED:
                try:
                    with SessionLocal.begin() as db:
                        task = (
                            self.task_service
                            .reset_claim_after_worker_restart(
                                db,
                                task_id,
                                self.worker_id,
                            )
                        )
                    print(
                        f"[worker] recovered queued task "
                        f"{task_id} -> {task.status.value}"
                    )
                except Exception as exc:
                    print(
                        f"[worker] failed to recover queued "
                        f"task {task_id}: {exc}"
                    )
                continue

            if status == TaskStatus.RUNNING:
                self._terminate_orphan_process_group(
                    task_id=task_id,
                    pgid=pgid,
                )

                if terminate_requested:
                    try:
                        with SessionLocal.begin() as db:
                            self.task_service.mark_terminated(
                                db,
                                task_id,
                                exit_code=None,
                            )
                        self._write_summary(task_id)
                        print(
                            f"[worker] recovered terminate "
                            f"request for {task_id}"
                        )
                    except Exception as exc:
                        print(
                            f"[worker] failed to persist "
                            f"recovered termination for "
                            f"{task_id}: {exc}"
                        )
                else:
                    self._mark_failed(
                        task_id,
                        "WORKER_RESTARTED",
                        (
                            "Worker restarted while task was "
                            "RUNNING; recorded process group "
                            "was terminated and the task was "
                            "marked FAILED."
                        ),
                    )

    def _shutdown_running_tasks(self) -> None:
        for task_id, running in list(
            self.running_tasks.items()
        ):
            print(
                f"[worker] stopping active task "
                f"{task_id} during worker shutdown"
            )

            self._terminate_orphan_process_group(
                task_id=task_id,
                pgid=running.pgid,
            )

            try:
                self._update_task_progress(running)
            except Exception as exc:
                print(
                    f"[worker] final progress update failed "
                    f"for {task_id}: {exc}"
                )

            self._mark_failed(
                task_id,
                "WORKER_STOPPED",
                "Worker stopped while task was RUNNING.",
            )
            del self.running_tasks[task_id]

    def _terminate_orphan_process_group(
        self,
        *,
        task_id: str,
        pgid: int | None,
    ) -> None:
        if pgid is None:
            return

        if not self._process_group_exists(pgid):
            return

        print(
            f"[worker] terminating orphan process group "
            f"task={task_id} pgid={pgid}"
        )

        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except PermissionError as exc:
            print(
                f"[worker] cannot SIGTERM pgid={pgid}: "
                f"{exc}"
            )
            return

        time.sleep(self.recovery_grace_seconds)

        if not self._process_group_exists(pgid):
            return

        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            print(
                f"[worker] cannot SIGKILL pgid={pgid}: "
                f"{exc}"
            )

    @staticmethod
    def _process_group_exists(pgid: int) -> bool:
        try:
            os.killpg(pgid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def _prepare_workspace(
            self,
            workspace_path: str,
    ) -> None:
        workspace = Path(
            workspace_path
        ).resolve()

        directories = [
            workspace / "input",
            workspace / "runtime",
            workspace / "logs",
            workspace / "result",
            workspace / "result" / "trace" / "dumps",
            ]

        for directory in directories:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

    def _build_mock_launch_spec(
            self,
            task,
    ) -> LaunchSpec:
        seconds = self.settings.sim_mock_run_seconds

        code = f"""
import time

steps = 6
sleep_time = {seconds} / steps

for i in range(1, steps + 1):
    cycle = i * 100
    print(
        f"[Sim: {{cycle}}(cycle)] mock simulator running",
        flush=True,
    )
    time.sleep(sleep_time)

print("mock simulator completed", flush=True)
"""

        workspace = Path(
            task.workspace_path
        ).resolve()

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

        return LaunchSpec(
            command=[
                sys.executable,
                "-c",
                code,
            ],
            cwd=Path.cwd(),
            env=os.environ.copy(),
            log_path=log_path,
            dump_dir=dump_dir,
        )

    def _build_launch_spec(
            self,
            task,
    ) -> LaunchSpec:
        if task.simulator_version == "mock":
            return self._build_mock_launch_spec(task)

        return self.simulator_adapter.build_launch_spec(
            task
        )

    def _mark_failed(
        self,
        task_id: str,
        error_code: str,
        error_message: str,
        exit_code: int | None = None,
    ) -> None:
        print(
            f"[worker] failed {task_id}: "
            f"{error_code}: {error_message}"
        )

        try:
            with SessionLocal.begin() as db:
                self.task_service.mark_failed(
                    db,
                    task_id,
                    error_code=error_code,
                    error_message=error_message,
                    exit_code=exit_code,
                )
            self._write_summary(task_id)
        except Exception as exc:
            print(
                f"[worker] failed to persist failure "
                f"for {task_id}: {exc}"
            )
    def _prepare_task_input(
            self,
            task,
    ) -> None:
        if task.simulator_version == "mock":
            return

        workspace = Path(
            task.workspace_path
        ).resolve()

        self.workload_resolver.resolve(
            input_workload_dir=(
                    workspace
                    / "input"
                    / "workload"
            ),
            resolved_workload_dir=(
                    workspace
                    / "runtime"
                    / "resolved_config"
                    / "workload"
            ),
        )

    def _update_task_progress(
            self,
            running: RunningTask,
    ) -> None:
        log_path = running.log_path
        latest_cycle = None
        new_offset = 0

        with SessionLocal() as db:
            task = self.repository.get_task(
                db,
                running.task_id,
            )

            if task is None:
                return

            offset = task.log_read_offset
            new_offset = offset

        if log_path.is_file():
            file_size = log_path.stat().st_size

            # 日志被截断或重新创建时，从头读取。
            if offset > file_size:
                offset = 0

            with log_path.open(
                    "r",
                    encoding="utf-8",
                    errors="replace",
            ) as log_file:
                log_file.seek(offset)
                new_text = log_file.read()
                new_offset = log_file.tell()

            if new_text:
                latest_cycle = (
                    self.cycle_parser.parse_latest_cycle(
                        new_text
                    )
                )

        # Runtime 与 Cycle 使用同一个 Worker 权威时间源。
        # 即使本轮日志没有新增内容，也持续更新 runtime_seconds。
        runtime_seconds = max(
            0.0,
            time.monotonic() - running.start_monotonic,
        )

        with SessionLocal.begin() as db:
            self.repository.update_progress(
                db,
                task_id=running.task_id,
                current_cycle=latest_cycle,
                log_read_offset=new_offset,
                runtime_seconds=runtime_seconds,
            )

    def _generate_trace(
            self,
            task_id: str,
            workspace_path: str,
    ) -> None:
        try:
            with SessionLocal.begin() as db:
                self.task_service.mark_trace_generating(
                    db,
                    task_id,
                )

            print(
                f"[worker] generating trace {task_id}"
            )

            result = self.trace_runner.run(
                workspace_path
            )

            if result.success:
                if self.settings.sim_trace_viewer_enabled:
                    viewer_result = self.trace_exporter.run(
                        workspace_path,
                        title=f"{task_id} · Simulation Trace",
                    )

                    if not viewer_result.success:
                        with SessionLocal.begin() as db:
                            self.task_service.mark_trace_failed(
                                db,
                                task_id,
                            )

                        print(
                            f"[worker] Catapult viewer failed "
                            f"{task_id}: "
                            f"{viewer_result.error_message}"
                        )
                        return

                with SessionLocal.begin() as db:
                    self.task_service.mark_trace_ready(
                        db,
                        task_id,
                    )

                print(
                    f"[worker] trace ready "
                    f"{task_id}: {result.trace_path}"
                )
                return

            with SessionLocal.begin() as db:
                self.task_service.mark_trace_failed(
                    db,
                    task_id,
                )

            print(
                f"[worker] trace failed "
                f"{task_id}: {result.error_message}"
            )

        except Exception as exc:
            # Trace 失败不能影响仿真任务最终进入 COMPLETED。
            print(
                f"[worker] trace handling failed "
                f"{task_id}: {exc}"
            )

            try:
                with SessionLocal.begin() as db:
                    self.task_service.mark_trace_failed(
                        db,
                        task_id,
                    )
            except Exception as persist_exc:
                print(
                    f"[worker] failed to persist trace failure "
                    f"{task_id}: {persist_exc}"
                )

    def _write_summary(
            self,
            task_id: str,
    ) -> None:
        try:
            with SessionLocal() as db:
                task = self.repository.get_task(
                    db,
                    task_id,
                )

                if task is None:
                    raise RuntimeError(
                        f"Task disappeared: {task_id}"
                    )

                summary_path = (
                    self.result_writer.write_summary(
                        task
                    )
                )

            print(
                f"[worker] summary ready "
                f"{task_id}: {summary_path}"
            )

        except Exception as exc:
            # summary 是派生结果。
            # 写入失败不能把已成功任务改成 FAILED。
            print(
                f"[worker] summary generation failed "
                f"{task_id}: {exc}"
            )

def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--until-idle",
        action="store_true",
        help=(
            "Exit when there are no running "
            "or claimable tasks."
        ),
    )

    args = parser.parse_args()

    worker = SimulationWorker()
    worker.run(
        until_idle=args.until_idle,
    )


if __name__ == "__main__":
    main()
