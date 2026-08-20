from typing import Any, Protocol


class BenchmarkResultProvider(Protocol):
    """Extension point for future MACRO/MICRO/TRACE result storage."""

    @property
    def configured(self) -> bool:
        ...

    def list_results(
        self,
        *,
        vendor: str,
        chip: str,
        benchmark_name: str,
    ) -> list[dict[str, Any]]:
        ...


class EmptyBenchmarkResultProvider:
    """V0.1 placeholder until the Benchmark result directory is defined."""

    @property
    def configured(self) -> bool:
        return False

    def list_results(
        self,
        *,
        vendor: str,
        chip: str,
        benchmark_name: str,
    ) -> list[dict[str, Any]]:
        return []
