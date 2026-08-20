import argparse
import shutil
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install a validated simulation input as a read-only sample template."
    )
    parser.add_argument("--source", required=True, help="Directory containing chip_config/ and workload/")
    parser.add_argument("--simulator-version", default="v310")
    parser.add_argument(
        "--target-root",
        default=str(BACKEND_ROOT / "config" / "simulation_templates"),
    )
    args = parser.parse_args()

    source = Path(args.source).resolve()
    chip = source / "chip_config"
    workload = source / "workload"
    if not chip.is_dir() or not workload.is_dir():
        raise SystemExit(
            "Source must contain chip_config/ and workload/ directories"
        )

    target = (
        Path(args.target_root).resolve()
        / args.simulator_version
        / "sample"
    )
    staging = target.parent / ".sample.installing"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    shutil.copytree(chip, staging / "chip_config")
    shutil.copytree(workload, staging / "workload")
    shutil.rmtree(target, ignore_errors=True)
    staging.replace(target)

    print(f"sample installed: {target}")
    print(f"chip_config files: {sum(1 for p in (target / 'chip_config').rglob('*') if p.is_file())}")
    print(f"workload files: {sum(1 for p in (target / 'workload').rglob('*') if p.is_file())}")


if __name__ == "__main__":
    main()
