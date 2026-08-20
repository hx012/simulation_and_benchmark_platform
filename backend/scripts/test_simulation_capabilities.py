import argparse
from pathlib import Path

from app.simulation.simulator.profiles import SimulatorProfileRegistry


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print backend-driven simulation capabilities from simulator_profiles.yml"
    )
    parser.add_argument(
        "--config",
        default="config/simulator_profiles.yml",
        help="Path to simulator profile YAML",
    )
    args = parser.parse_args()

    registry = SimulatorProfileRegistry(Path(args.config).resolve())
    capabilities = registry.get_capabilities()

    print(f"simulators={len(capabilities)}")
    for simulator in capabilities:
        print(f"- {simulator.label} [{simulator.key}]")
        for variant in simulator.variants:
            print(f"  - {variant.label} [{variant.key}]")
            for mode in variant.modes:
                print(f"    - {mode.label} [{mode.key.value}]")


if __name__ == "__main__":
    main()
