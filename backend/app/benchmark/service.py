from app.benchmark.registry_reader import BenchmarkRegistryReader
from app.benchmark.result_provider import BenchmarkResultProvider
from app.benchmark.schemas import (
    BenchmarkDefinition,
    BenchmarkResultListResponse,
    ChipDetail,
    ChipSummary,
)


class BenchmarkService:
    def __init__(
        self,
        *,
        registry_reader: BenchmarkRegistryReader,
        result_provider: BenchmarkResultProvider,
    ):
        self._registry_reader = registry_reader
        self._result_provider = result_provider

    @property
    def registry_available(self) -> bool:
        return self._registry_reader.configured

    @property
    def results_available(self) -> bool:
        return self._result_provider.configured

    def list_chips(self) -> list[ChipSummary]:
        return self._registry_reader.list_chips()

    def get_chip(self, vendor: str, chip: str) -> ChipDetail:
        return self._registry_reader.get_chip(vendor, chip)

    def list_benchmarks(self, vendor: str, chip: str) -> list[BenchmarkDefinition]:
        return self._registry_reader.list_benchmarks(vendor, chip)

    def get_benchmark(
        self,
        vendor: str,
        chip: str,
        benchmark_name: str,
    ) -> BenchmarkDefinition:
        return self._registry_reader.get_benchmark(vendor, chip, benchmark_name)

    def list_results(
        self,
        vendor: str,
        chip: str,
        benchmark_name: str,
    ) -> BenchmarkResultListResponse:
        # Validate the benchmark first so an unknown benchmark still returns 404
        # rather than looking like a valid benchmark with zero results.
        self._registry_reader.get_benchmark(vendor, chip, benchmark_name)
        items = self._result_provider.list_results(
            vendor=vendor,
            chip=chip,
            benchmark_name=benchmark_name,
        )
        return BenchmarkResultListResponse(
            vendor=vendor,
            chip=chip,
            benchmark_name=benchmark_name,
            configured=self._result_provider.configured,
            items=items,
            total=len(items),
        )
