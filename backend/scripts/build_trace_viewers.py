from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.common.config import get_settings  # noqa: E402
from app.simulation.catapult_trace_exporter import (  # noqa: E402
    CatapultTraceExporter,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Catapult HTML viewers for existing task traces."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--task-id")
    target.add_argument("--all", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def list_workspaces(task_root: Path, task_id: str | None) -> list[Path]:
    if task_id:
        if not task_id or any(
            character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
            for character in task_id
        ):
            raise ValueError(f"Invalid task ID: {task_id}")
        workspace = (task_root / task_id).resolve()
        workspace.relative_to(task_root)
        return [workspace]

    return sorted(path.resolve() for path in task_root.iterdir() if path.is_dir())


def main() -> int:
    args = parse_args()
    settings = get_settings()
    task_root = Path(settings.task_root).resolve()
    exporter = CatapultTraceExporter(settings)

    if not task_root.is_dir():
        print(f"Task root does not exist: {task_root}", file=sys.stderr)
        return 2

    generated = 0
    skipped = 0
    failed = 0

    for workspace in list_workspaces(task_root, args.task_id):
        source = workspace / "result" / "trace" / "dumps" / "trace.json"
        viewer = workspace / "result" / "trace" / "trace.html"

        if not source.is_file():
            skipped += 1
            continue
        if viewer.is_file() and not args.force:
            print(f"skip existing: {workspace.name}")
            skipped += 1
            continue
        if args.dry_run:
            print(f"would generate: {workspace.name}")
            generated += 1
            continue

        result = exporter.run(
            str(workspace),
            title=f"{workspace.name} · Simulation Trace",
        )
        if result.success:
            print(f"generated: {result.trace_html_path}")
            generated += 1
        else:
            print(
                f"failed: {workspace.name}: {result.error_message}",
                file=sys.stderr,
            )
            failed += 1

    print(
        f"summary: generated={generated} skipped={skipped} failed={failed}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
