from functools import lru_cache
from pathlib import Path

import yaml

from app.recent_activity.schemas import RecentActivityConfig


@lru_cache(maxsize=8)
def _load_config(path_value: str, modified_ns: int) -> RecentActivityConfig:
    del modified_ns
    path = Path(path_value)
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return RecentActivityConfig.model_validate(payload)


def load_recent_activity_config(path: Path) -> RecentActivityConfig:
    stat = path.stat()
    return _load_config(str(path.resolve()), stat.st_mtime_ns)
