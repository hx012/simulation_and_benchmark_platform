from functools import lru_cache
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.common.config import DEFAULT_PLATFORM_ENV_FILE


class BenchmarkSettings(BaseSettings):
    """Configuration used by the Benchmark read-only backend.

    AIBENCH_HOME should point to the Python package directory that contains
    both ``registry/`` and ``benchmark/`` in the existing aibench project.
    """

    aibench_home: Path | None = None

    model_config = SettingsConfigDict(
        env_file=DEFAULT_PLATFORM_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_benchmark_settings() -> BenchmarkSettings:
    env_file = os.environ.get("PLATFORM_ENV_FILE", str(DEFAULT_PLATFORM_ENV_FILE))
    return BenchmarkSettings(_env_file=env_file)
