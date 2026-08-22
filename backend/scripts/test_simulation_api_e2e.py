import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


TERMINAL_STATUSES = {
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "TERMINATED",
}

COOKIE_JAR: Path | None = None


def run_curl(args: list[str]) -> Any:
    command = [
        "curl",
        "-sS",
        *(["-b", str(COOKIE_JAR), "-c", str(COOKIE_JAR)] if COOKIE_JAR else []),
        *args,
    ]

    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        print("curl command failed:", file=sys.stderr)
        print(" ".join(command), file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        raise SystemExit(result.returncode)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(
            f"Expected JSON response, got:\n{result.stdout}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


def upload_directory(
    *,
    base_url: str,
    upload_session_id: str,
    package_endpoint: str,
    root: Path,
) -> Any:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
    )

    if not files:
        raise SystemExit(
            f"No files found under {root}"
        )

    curl_args = [
        "-X",
        "PUT",
        (
            f"{base_url}/api/simulation/upload-sessions/"
            f"{upload_session_id}/{package_endpoint}"
        ),
    ]

    for path in files:
        relative = path.relative_to(root).as_posix()
        curl_args.extend(
            [
                "-F",
                f"files=@{path}",
                "-F",
                f"relative_paths={relative}",
            ]
        )

    return run_curl(curl_args)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "End-to-end Simulation API test: upload -> validate -> "
            "submit -> queue/worker -> result. Start FastAPI and the "
            "Simulation Worker before running this script."
        )
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--chip-config-dir",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--workload-dir",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--owner-id",
        default="admin",
    )
    parser.add_argument(
        "--task-name",
        default="Simulation API E2E Test",
    )
    parser.add_argument(
        "--simulator-version",
        default="v310",
    )
    parser.add_argument(
        "--chip-variant",
        default=None,
    )
    parser.add_argument(
        "--simulation-mode",
        default="SINGLE_CHIP",
        choices=["SINGLE_CHIP", "MULTI_CHIP"],
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=1.0,
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=300.0,
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
    )
    args = parser.parse_args()

    global COOKIE_JAR
    cookie_file = tempfile.NamedTemporaryFile(prefix="platform-e2e-", suffix=".cookie")
    COOKIE_JAR = Path(cookie_file.name)

    base_url = args.base_url.rstrip("/")
    chip_config_dir = args.chip_config_dir.resolve()
    workload_dir = args.workload_dir.resolve()

    login = run_curl([
        "-X", "POST", f"{base_url}/api/auth/login",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"employee_id": args.owner_id, "auth_mode": "normal"}),
    ])
    if login.get("user_id") != args.owner_id:
        raise SystemExit("Failed to establish the expected platform session")

    if not chip_config_dir.is_dir():
        raise SystemExit(
            f"chip-config-dir is not a directory: {chip_config_dir}"
        )

    if not workload_dir.is_dir():
        raise SystemExit(
            f"workload-dir is not a directory: {workload_dir}"
        )

    session = run_curl(
        [
            "-X",
            "POST",
            f"{base_url}/api/simulation/upload-sessions",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps({"owner_id": args.owner_id}),
        ]
    )
    upload_session_id = session["upload_session_id"]
    print("upload_session_id =", upload_session_id)

    workload_response = upload_directory(
        base_url=base_url,
        upload_session_id=upload_session_id,
        package_endpoint="workload",
        root=workload_dir,
    )
    print(
        "workload uploaded =",
        workload_response["uploaded_files"],
    )

    chip_response = upload_directory(
        base_url=base_url,
        upload_session_id=upload_session_id,
        package_endpoint="chip-config",
        root=chip_config_dir,
    )
    print(
        "chip_config uploaded =",
        chip_response["uploaded_files"],
    )

    validation = run_curl(
        [
            "-X",
            "POST",
            (
                f"{base_url}/api/simulation/upload-sessions/"
                f"{upload_session_id}/validate"
            ),
        ]
    )

    print(
        "validation =",
        json.dumps(
            validation,
            ensure_ascii=False,
            indent=2,
        ),
    )

    if not validation.get("valid"):
        raise SystemExit(2)

    submit_payload = {
        "task_name": args.task_name,
        "simulator_version": args.simulator_version,
        "chip_variant": args.chip_variant,
        "simulation_mode": args.simulation_mode,
    }

    submitted = run_curl(
        [
            "-X",
            "POST",
            (
                f"{base_url}/api/simulation/upload-sessions/"
                f"{upload_session_id}/submit"
            ),
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(submit_payload),
        ]
    )

    task_id = submitted["task"]["task_id"]
    print("task_id =", task_id)
    print("queued_ahead =", submitted["queued_ahead"])

    if args.no_wait:
        return

    deadline = time.monotonic() + args.timeout_seconds

    while True:
        task = run_curl(
            [
                f"{base_url}/api/simulation/tasks/{task_id}"
            ]
        )

        status = task["status"]
        current_cycle = task.get("current_cycle")
        print(
            f"status={status} current_cycle={current_cycle}"
        )

        if status in TERMINAL_STATUSES:
            break

        if time.monotonic() >= deadline:
            raise SystemExit(
                f"Timed out waiting for task {task_id}"
            )

        time.sleep(args.poll_seconds)

    result = run_curl(
        [
            f"{base_url}/api/simulation/tasks/{task_id}/result"
        ]
    )

    print(
        "result =",
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
    )

    if status != "COMPLETED":
        raise SystemExit(3)


if __name__ == "__main__":
    main()
