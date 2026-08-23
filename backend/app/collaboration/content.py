from pathlib import Path
from urllib.parse import urlparse

import yaml

from app.collaboration.schemas import CommunityLink, TeamConfigResponse
from app.common.config import Settings


DEFAULT_TEAM = {
    "name": "芯片仿真与性能分析团队",
    "description": "面向 AI 芯片架构研究与工程验证，提供仿真、Benchmark、Trace 与性能分析能力。",
    "team_size": "",
    "specialties": ["架构仿真", "负载建模", "性能分析"],
    "achievements": [],
    "contributions": [],
}


def _read_content(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload if isinstance(payload, dict) else {}


def load_team_config(settings: Settings) -> TeamConfigResponse:
    payload = _read_content(settings.platform_content_config)
    team = payload.get("team") if isinstance(payload.get("team"), dict) else DEFAULT_TEAM
    merged = {**DEFAULT_TEAM, **team}
    return TeamConfigResponse.model_validate(merged)


def load_demand_reviews(settings: Settings) -> dict[str, dict]:
    payload = _read_content(settings.platform_content_config)
    reviews = payload.get("demand_reviews", {})
    return reviews if isinstance(reviews, dict) else {}


def community_links(settings: Settings) -> list[CommunityLink]:
    values = [
        ("w3", settings.platform_community_w3_name, settings.platform_community_w3_url),
        ("jiaxian", settings.platform_community_jiaxian_name, settings.platform_community_jiaxian_url),
    ]
    result: list[CommunityLink] = []
    for key, name, url in values:
        normalized = url.strip()
        parsed = urlparse(normalized)
        enabled = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        result.append(CommunityLink(
            key=key,
            name=name.strip() or key,
            url=normalized if enabled else "",
            enabled=enabled,
        ))
    return result
