import json
from pathlib import Path
from typing import Any

from app.benchmark.exceptions import (
    BenchmarkChipNotFoundError,
    BenchmarkDefinitionNotFoundError,
    BenchmarkNotConfiguredError,
    BenchmarkRegistryFormatError,
    BenchmarkRegistryNotFoundError,
)
from app.benchmark.schemas import BenchmarkDefinition, ChipDetail, ChipSummary


class BenchmarkRegistryReader:
    """Read chip/benchmark definitions directly from the existing aibench registry.

    This class deliberately does not invoke ``aibench`` CLI and does not infer
    category/target from Python module paths.  The registry JSON is the source
    of truth.  Optional future fields such as ``category`` and ``target`` are
    passed through when present.
    """

    def __init__(self, aibench_home: Path | None):
        self._aibench_home = aibench_home.resolve() if aibench_home else None

    @property
    def configured(self) -> bool:
        return self._aibench_home is not None

    @property
    def chip_registry_path(self) -> Path:
        home = self._require_home()
        return home / "registry" / "chip_registry.json"

    def list_chips(self) -> list[ChipSummary]:
        registry = self._load_chip_registry()
        chips: list[ChipSummary] = []

        for key, raw in registry.items():
            if not isinstance(raw, dict):
                raise BenchmarkRegistryFormatError(
                    f"chip_registry entry must be an object: {key}"
                )
            vendor = self._required_str(raw, "vendor", context=f"chip {key}")
            chip = self._required_str(raw, "chip", context=f"chip {key}")
            chips.append(ChipSummary(vendor=vendor, chip=chip))

        chips.sort(key=lambda item: (item.vendor, item.chip))
        return chips

    def get_chip(self, vendor: str, chip: str) -> ChipDetail:
        raw = self._find_chip_entry(vendor, chip)
        benchmarks = self._load_benchmark_registry(raw)

        return ChipDetail(
            vendor=vendor,
            chip=chip,
            benchmark_dir=self._required_str(
                raw,
                "benchmark_dir",
                context=f"chip {vendor}/{chip}",
            ),
            benchmark_registry=self._required_str(
                raw,
                "benchmark_registry",
                context=f"chip {vendor}/{chip}",
            ),
            benchmark_count=len(benchmarks),
        )

    def list_benchmarks(self, vendor: str, chip: str) -> list[BenchmarkDefinition]:
        raw_chip = self._find_chip_entry(vendor, chip)
        raw_benchmarks = self._load_benchmark_registry(raw_chip)
        definitions = [
            self._to_definition(vendor, chip, name, raw)
            for name, raw in raw_benchmarks.items()
        ]
        definitions.sort(key=lambda item: item.name)
        return definitions

    def get_benchmark(
        self,
        vendor: str,
        chip: str,
        benchmark_name: str,
    ) -> BenchmarkDefinition:
        raw_chip = self._find_chip_entry(vendor, chip)
        raw_benchmarks = self._load_benchmark_registry(raw_chip)
        raw = raw_benchmarks.get(benchmark_name)
        if raw is None:
            raise BenchmarkDefinitionNotFoundError(
                f"Benchmark not registered: {vendor}/{chip}/{benchmark_name}"
            )
        return self._to_definition(vendor, chip, benchmark_name, raw)

    def _require_home(self) -> Path:
        if self._aibench_home is None:
            raise BenchmarkNotConfiguredError(
                "AIBENCH_HOME is not configured. Set it to the aibench package "
                "directory containing registry/ and benchmark/."
            )
        return self._aibench_home

    def _load_chip_registry(self) -> dict[str, Any]:
        path = self.chip_registry_path
        data = self._load_json(path)
        if not isinstance(data, dict):
            raise BenchmarkRegistryFormatError(
                f"chip_registry.json root must be an object: {path}"
            )
        return data

    def _find_chip_entry(self, vendor: str, chip: str) -> dict[str, Any]:
        registry = self._load_chip_registry()
        for key, raw in registry.items():
            if not isinstance(raw, dict):
                raise BenchmarkRegistryFormatError(
                    f"chip_registry entry must be an object: {key}"
                )
            if raw.get("vendor") == vendor and raw.get("chip") == chip:
                return raw
        raise BenchmarkChipNotFoundError(f"Chip not registered: {vendor}/{chip}")

    def _load_benchmark_registry(self, chip_entry: dict[str, Any]) -> dict[str, Any]:
        relative_path = self._required_str(
            chip_entry,
            "benchmark_registry",
            context="chip registry entry",
        )
        path = self._resolve_aibench_path(relative_path)
        data = self._load_json(path)
        if not isinstance(data, dict):
            raise BenchmarkRegistryFormatError(
                f"benchmark registry root must be an object: {path}"
            )
        benchmarks = data.get("benchmarks", {})
        if not isinstance(benchmarks, dict):
            raise BenchmarkRegistryFormatError(
                f"'benchmarks' must be an object: {path}"
            )
        return benchmarks

    def _resolve_aibench_path(self, configured_path: str) -> Path:
        home = self._require_home()
        candidate = Path(configured_path)
        path = candidate if candidate.is_absolute() else home / candidate
        path = path.resolve()

        # Registry data is trusted project configuration, but keep file reads
        # inside AIBENCH_HOME so a malformed registry cannot escape the tree.
        try:
            path.relative_to(home)
        except ValueError as exc:
            raise BenchmarkRegistryFormatError(
                f"Registry path escapes AIBENCH_HOME: {configured_path}"
            ) from exc
        return path

    @staticmethod
    def _load_json(path: Path) -> Any:
        if not path.is_file():
            raise BenchmarkRegistryNotFoundError(f"Registry file not found: {path}")
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError as exc:
            raise BenchmarkRegistryFormatError(
                f"Invalid JSON in registry file {path}: {exc}"
            ) from exc

    @staticmethod
    def _required_str(raw: dict[str, Any], field: str, *, context: str) -> str:
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            raise BenchmarkRegistryFormatError(
                f"Missing or invalid '{field}' in {context}"
            )
        return value

    def _to_definition(
        self,
        vendor: str,
        chip: str,
        registry_key: str,
        raw: Any,
    ) -> BenchmarkDefinition:
        if not isinstance(raw, dict):
            raise BenchmarkRegistryFormatError(
                f"Benchmark entry must be an object: {registry_key}"
            )

        name = raw.get("name", registry_key)
        if not isinstance(name, str) or not name.strip():
            raise BenchmarkRegistryFormatError(
                f"Invalid benchmark name: {vendor}/{chip}/{registry_key}"
            )

        module = self._required_str(
            raw,
            "module",
            context=f"benchmark {vendor}/{chip}/{registry_key}",
        )
        class_name = self._required_str(
            raw,
            "class_name",
            context=f"benchmark {vendor}/{chip}/{registry_key}",
        )

        description = raw.get("description", "")
        if not isinstance(description, str):
            description = str(description)

        category = raw.get("category")
        if category is not None and not isinstance(category, str):
            category = str(category)

        target = raw.get("target")
        if target is not None and not isinstance(target, str):
            target = str(target)

        return BenchmarkDefinition(
            benchmark_id=f"{vendor}.{chip}.{name}",
            vendor=vendor,
            chip=chip,
            name=name,
            module=module,
            class_name=class_name,
            description=description,
            category=category,
            target=target,
        )
