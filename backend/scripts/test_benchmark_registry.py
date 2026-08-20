import argparse
from pathlib import Path

from app.benchmark.registry_reader import BenchmarkRegistryReader


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test the aibench registry adapter")
    parser.add_argument(
        "--aibench-home",
        required=True,
        help="Path containing aibench registry/ and benchmark/ directories",
    )
    args = parser.parse_args()

    reader = BenchmarkRegistryReader(Path(args.aibench_home))
    chips = reader.list_chips()

    print(f"chips={len(chips)}")
    for chip in chips:
        benchmarks = reader.list_benchmarks(chip.vendor, chip.chip)
        print(f"- {chip.vendor}/{chip.chip}: benchmarks={len(benchmarks)}")
        for benchmark in benchmarks:
            print(
                "  - "
                f"{benchmark.name} | "
                f"{benchmark.description} | "
                f"category={benchmark.category or '-'} | "
                f"target={benchmark.target or '-'}"
            )


if __name__ == "__main__":
    main()
