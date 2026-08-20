from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class BenchmarkSettings(BaseSettings):
    """Configuration used by the Benchmark read-only backend.

    AIBENCH_HOME should point to the Python package directory that contains
    both ``registry/`` and ``benchmark/`` in the existing aibench project.
    """

    aibench_home: Path | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_benchmark_settings() -> BenchmarkSettings:
    return BenchmarkSettings()
