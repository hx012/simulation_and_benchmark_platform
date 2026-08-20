from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Ascend Simulator & Benchmark Platform"
    app_version: str = "0.1.0"
    app_env: str = "development"

    task_root: Path = Path("./data/simulation_tasks")

    simulator_home: Path | None = None
    sst_executable: Path | None = None
    database_url: str | None = None

    sim_worker_id: str = "simulation-worker-01"
    sim_max_concurrent_tasks: int = 2
    sim_worker_poll_interval_seconds: float = 0.5
    sim_mock_run_seconds: float = 6.0
    sim_progress_update_interval_seconds: float = 3.0
    sim_user_task_limit: int = 30
    sim_terminate_grace_seconds: float = 3.0
    sim_worker_recovery_grace_seconds: float = 1.0

    sim_log_max_chunk_bytes: int = 1024 * 1024
    sim_trace_max_bytes: int = 64 * 1024 * 1024
    sim_online_edit_max_bytes: int = 2 * 1024 * 1024
    sim_sample_template_root: Path = BACKEND_ROOT / "config" / "simulation_templates"

    upload_session_ttl_hours: float = 24.0
    upload_cleanup_batch_size: int = 100
    upload_submit_lock_stale_seconds: float = 600.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
