from functools import lru_cache
import os
from pathlib import Path
from urllib.parse import quote

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
DEFAULT_PLATFORM_ENV_FILE = PROJECT_ROOT / ".env.platform"


class Settings(BaseSettings):
    app_name: str = "Ascend Simulator & Benchmark Platform"
    app_version: str = "0.1.0"
    app_env: str = "development"
    # Used only to create/recover the first administrator. Additional admins live in DB.
    platform_bootstrap_admin_id: str = "admin"
    platform_bootstrap_admin_password: str = ""
    platform_session_hours: float = 12.0
    platform_session_cookie_secure: bool = False
    platform_w3_oauth_enabled: bool = False
    platform_w3_client_id: str = ""
    platform_w3_client_secret: str = ""
    platform_w3_authorize_url: str = "https://uniportal.huawei.com/saaslogin1/oauth2/authorize"
    platform_w3_token_url: str = "https://uniportal.huawei.com/saaslogin1/oauth2/accesstoken"
    platform_w3_userinfo_url: str = "https://uniportal.huawei.com/saaslogin1/oauth2/userinfo"
    platform_w3_redirect_uri: str = ""
    platform_w3_scope: str = "base.profile"
    platform_w3_http_timeout_seconds: float = 15.0
    platform_w3_state_ttl_seconds: int = 600
    platform_community_w3_name: str = "W3 负载建模社区"
    platform_community_w3_url: str = ""
    platform_community_jiaxian_name: str = "稼先社区"
    platform_community_jiaxian_url: str = ""
    platform_content_config: Path = BACKEND_ROOT / "config" / "platform_content.yml"

    task_root: Path = Path("./data/simulation_tasks")

    simulator_home: Path | None = None
    simulator_profiles_file: Path = BACKEND_ROOT / "config" / "simulator_profiles.yml"
    sst_executable: Path | None = None
    database_url: str | None = None
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 15432
    postgres_user: str = "ascend_platform"
    postgres_password: str = ""
    postgres_db: str = "ascend_platform"

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
    sim_trace_viewer_enabled: bool = True
    sim_trace_viewer_config: str = "full"
    sim_trace_viewer_timeout_seconds: float = 120.0
    sim_trace_viewer_max_output_bytes: int = 256 * 1024 * 1024
    sim_online_edit_max_bytes: int = 2 * 1024 * 1024
    sim_sample_template_root: Path = BACKEND_ROOT / "config" / "simulation_templates"

    catapult_home: Path = BACKEND_ROOT.parent / "tools" / "catapult"
    catapult_python: Path | None = None

    upload_session_ttl_hours: float = 24.0
    upload_cleanup_batch_size: int = 100
    upload_submit_lock_stale_seconds: float = 600.0

    # Raw analytics events are periodically removed by the simulation worker.
    # Set retention to 0 to keep events indefinitely.
    analytics_event_retention_days: int = 180
    analytics_cleanup_interval_hours: float = 24.0

    model_config = SettingsConfigDict(
        env_file=DEFAULT_PLATFORM_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def derive_database_url(self) -> "Settings":
        if self.database_url is not None or not self.postgres_password:
            return self
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password, safe="")
        database = quote(self.postgres_db, safe="")
        self.database_url = (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{database}"
        )
        return self

    @model_validator(mode="after")
    def validate_w3_oauth(self) -> "Settings":
        if not self.platform_w3_oauth_enabled:
            return self
        required = {
            "PLATFORM_W3_CLIENT_ID": self.platform_w3_client_id,
            "PLATFORM_W3_CLIENT_SECRET": self.platform_w3_client_secret,
            "PLATFORM_W3_REDIRECT_URI": self.platform_w3_redirect_uri,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise ValueError(f"W3 OAuth2 is enabled but settings are missing: {', '.join(missing)}")
        return self

    @model_validator(mode="after")
    def validate_analytics_retention(self) -> "Settings":
        if self.analytics_event_retention_days < 0:
            raise ValueError("ANALYTICS_EVENT_RETENTION_DAYS must be 0 or greater")
        if self.analytics_cleanup_interval_hours <= 0:
            raise ValueError("ANALYTICS_CLEANUP_INTERVAL_HOURS must be greater than 0")
        return self


@lru_cache
def get_settings() -> Settings:
    env_file = os.environ.get("PLATFORM_ENV_FILE", str(DEFAULT_PLATFORM_ENV_FILE))
    return Settings(_env_file=env_file)
