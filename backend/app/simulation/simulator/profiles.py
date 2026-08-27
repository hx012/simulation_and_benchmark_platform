from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml

from app.simulation.enums import SimulationMode


DEFAULT_VARIANT_KEY = "default"


def normalize_guide_url(value: object) -> str:
    normalized = str(value or "").strip()
    if normalized.startswith("/") and not normalized.startswith("//"):
        return normalized
    parsed = urlparse(normalized)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return normalized
    return ""


def normalize_variant_key(chip_variant: str | None) -> str:
    if chip_variant is None:
        return DEFAULT_VARIANT_KEY
    value = chip_variant.strip()
    if not value or value.lower() == DEFAULT_VARIANT_KEY:
        return DEFAULT_VARIANT_KEY
    return value


def default_simulator_label(simulator_version: str) -> str:
    value = simulator_version.strip()
    if value.lower().startswith("v") and value[1:].isdigit():
        return value.upper()
    return value


def default_variant_label(chip_variant: str | None) -> str:
    key = normalize_variant_key(chip_variant)
    if key == DEFAULT_VARIANT_KEY:
        return "默认"
    return key


def default_mode_label(simulation_mode: SimulationMode) -> str:
    if simulation_mode == SimulationMode.SINGLE_CHIP:
        return "单芯片"
    if simulation_mode == SimulationMode.MULTI_CHIP:
        return "多芯片"
    return simulation_mode.value


@dataclass(frozen=True)
class SimulatorProfile:
    simulator_version: str
    simulator_label: str
    chip_variant: str | None
    chip_variant_key: str
    chip_variant_label: str
    simulation_mode: SimulationMode
    simulation_mode_label: str
    entry_script: str
    sst_args: list[str]


@dataclass(frozen=True)
class SimulationModeCapability:
    key: SimulationMode
    label: str


@dataclass(frozen=True)
class ChipVariantCapability:
    key: str
    label: str
    modes: list[SimulationModeCapability]


@dataclass(frozen=True)
class SimulatorCapability:
    key: str
    label: str
    variants: list[ChipVariantCapability]


class SimulatorProfileNotFoundError(Exception):
    pass


class SimulatorProfileRegistry:
    def __init__(
        self,
        config_path: Path,
    ) -> None:
        self.config_path = config_path
        self.profiles = self._load_profiles()

    def _load_profiles(
        self,
    ) -> list[SimulatorProfile]:
        with self.config_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = yaml.safe_load(file) or {}

        self.mskpp_guide_url = normalize_guide_url(
            data.get("mskpp_guide_url")
        )

        profiles: list[SimulatorProfile] = []
        seen_keys: set[tuple[str, str, SimulationMode]] = set()

        for item in data.get("profiles", []):
            simulator_version = str(item["simulator_version"])
            chip_variant = item.get("chip_variant")
            if chip_variant is not None:
                chip_variant = str(chip_variant)
            simulation_mode = SimulationMode(item["simulation_mode"])
            variant_key = normalize_variant_key(chip_variant)
            profile_key = (simulator_version, variant_key, simulation_mode)
            if profile_key in seen_keys:
                raise ValueError(
                    "Duplicate simulator profile: "
                    f"version={simulator_version}, "
                    f"variant={variant_key}, "
                    f"mode={simulation_mode.value}"
                )
            seen_keys.add(profile_key)

            profiles.append(
                SimulatorProfile(
                    simulator_version=simulator_version,
                    simulator_label=str(
                        item.get("simulator_label")
                        or default_simulator_label(simulator_version)
                    ),
                    chip_variant=chip_variant,
                    chip_variant_key=variant_key,
                    chip_variant_label=str(
                        item.get("chip_variant_label")
                        or default_variant_label(chip_variant)
                    ),
                    simulation_mode=simulation_mode,
                    simulation_mode_label=str(
                        item.get("simulation_mode_label")
                        or default_mode_label(simulation_mode)
                    ),
                    entry_script=item["entry_script"],
                    sst_args=list(item.get("sst_args", [])),
                )
            )

        return profiles

    def get_profile(
        self,
        simulator_version: str,
        chip_variant: str | None,
        simulation_mode: SimulationMode,
    ) -> SimulatorProfile:
        requested_variant_key = normalize_variant_key(chip_variant)

        for profile in self.profiles:
            if (
                profile.simulator_version == simulator_version
                and profile.chip_variant_key == requested_variant_key
                and profile.simulation_mode == simulation_mode
            ):
                return profile

        raise SimulatorProfileNotFoundError(
            "Simulator profile not found: "
            f"version={simulator_version}, "
            f"variant={requested_variant_key}, "
            f"mode={simulation_mode.value}"
        )

    def get_capabilities(self) -> list[SimulatorCapability]:
        simulators: dict[str, dict] = {}

        for profile in self.profiles:
            simulator = simulators.setdefault(
                profile.simulator_version,
                {
                    "label": profile.simulator_label,
                    "variants": {},
                },
            )
            variants = simulator["variants"]
            variant = variants.setdefault(
                profile.chip_variant_key,
                {
                    "label": profile.chip_variant_label,
                    "modes": {},
                },
            )
            variant["modes"][profile.simulation_mode] = profile.simulation_mode_label

        result: list[SimulatorCapability] = []
        for simulator_key, simulator in simulators.items():
            variant_items: list[ChipVariantCapability] = []
            for variant_key, variant in simulator["variants"].items():
                modes = [
                    SimulationModeCapability(key=mode_key, label=mode_label)
                    for mode_key, mode_label in variant["modes"].items()
                ]
                variant_items.append(
                    ChipVariantCapability(
                        key=variant_key,
                        label=variant["label"],
                        modes=modes,
                    )
                )

            result.append(
                SimulatorCapability(
                    key=simulator_key,
                    label=simulator["label"],
                    variants=variant_items,
                )
            )

        return result
