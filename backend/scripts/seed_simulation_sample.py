import argparse
import shutil
from pathlib import Path

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install validated Chip Config and Workload template directories."
    )
    parser.add_argument("--source", required=True, help="Directory containing chip_config/ and workload/")
    parser.add_argument("--chip-config-target", required=True)
    parser.add_argument("--workload-target", required=True)
    args = parser.parse_args()

    source = Path(args.source).resolve()
    chip = source / "chip_config"
    workload = source / "workload"
    if not chip.is_dir() or not workload.is_dir():
        raise SystemExit(
            "Source must contain chip_config/ and workload/ directories"
        )

    targets = (
        ("chip_config", chip, Path(args.chip_config_target).resolve()),
        ("workload", workload, Path(args.workload_target).resolve()),
    )
    for label, source_dir, target in targets:
        staging = target.parent / f".{target.name}.installing"
        shutil.rmtree(staging, ignore_errors=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, staging)
        shutil.rmtree(target, ignore_errors=True)
        staging.replace(target)
        count = sum(1 for path in target.rglob("*") if path.is_file())
        print(f"{label} installed: {target} ({count} files)")


if __name__ == "__main__":
    main()
