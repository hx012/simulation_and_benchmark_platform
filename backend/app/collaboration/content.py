from datetime import date
from pathlib import Path
import logging
from urllib.parse import urlparse
from urllib.parse import quote

import yaml

from app.collaboration.schemas import (
    CommunityLink,
    FeatureReleaseConfigResponse,
    PlatformSupport,
    TeamConfigResponse,
)
from app.common.config import Settings


DEFAULT_TEAM = {
    "name": "芯片仿真与性能分析团队",
    "description": "面向 AI 芯片架构研究与工程验证，提供仿真、Benchmark、Trace 与性能分析能力。",
    "team_size": "",
    "specialties": ["架构仿真", "负载建模", "性能分析"],
    "members": [],
    "achievements": [],
    "contributions": [],
    "all_achievements_url": "",
}

DEFAULT_FEATURE_RELEASES = {
    "enabled": True,
    "title": "新特性上线",
    "max_items": 3,
    "new_badge_days": 14,
    "items": [],
}

logger = logging.getLogger(__name__)


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
    result = TeamConfigResponse.model_validate(merged)
    result.members = sorted(
        (member for member in result.members if member.enabled),
        key=lambda member: member.order,
    )
    for member in result.members:
        filename = Path(member.avatar_file).name
        if filename == member.avatar_file and Path(filename).suffix.lower() in {".webp", ".png", ".jpg", ".jpeg"}:
            member.avatar_url = f"/api/team/avatars/{quote(filename)}"
        else:
            member.avatar_url = ""
    result.achievements = [item for item in result.achievements if item.enabled]
    featured_count = sum(1 for item in result.achievements if item.featured)
    if featured_count > 5:
        logger.warning(
            "platform content enables %s featured achievements; the home page shows only 5",
            featured_count,
        )
    return result


def load_feature_releases(
    settings: Settings,
    *,
    today: date | None = None,
) -> FeatureReleaseConfigResponse:
    payload = _read_content(settings.platform_content_config)
    configured = payload.get("feature_releases")
    merged = {
        **DEFAULT_FEATURE_RELEASES,
        **(configured if isinstance(configured, dict) else {}),
    }
    result = FeatureReleaseConfigResponse.model_validate(merged)
    if not result.enabled:
        result.items = []
        return result

    current_date = today or date.today()
    result.items = sorted(
        (
            item
            for item in result.items
            if item.enabled and item.launched_at <= current_date
        ),
        key=lambda item: (item.launched_at, item.id),
        reverse=True,
    )
    for item in result.items:
        item.action_url = _safe_content_url(item.action_url)
    return result


def _safe_content_url(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("/") and not normalized.startswith("//"):
        return normalized
    parsed = urlparse(normalized)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return normalized
    return ""


def load_demand_reviews(settings: Settings) -> dict[str, dict]:
    payload = _read_content(settings.platform_content_config)
    reviews = payload.get("demand_reviews", {})
    return reviews if isinstance(reviews, dict) else {}


def community_links(settings: Settings) -> list[CommunityLink]:
    payload = _read_content(settings.platform_content_config)
    configured = payload.get("communities", [])
    configured_by_key = {
        str(item.get("key")): item
        for item in configured
        if isinstance(item, dict) and item.get("key")
    } if isinstance(configured, list) else {}
    values = [
        ("jiaxian", settings.platform_community_jiaxian_name, settings.platform_community_jiaxian_url, 10),
        ("w3", settings.platform_community_w3_name, settings.platform_community_w3_url, 20),
        ("benchmark_wiki", "Benchmark Wiki", "", 30),
    ]
    result: list[CommunityLink] = []
    for key, default_name, default_url, default_order in values:
        override = configured_by_key.get(key, {})
        name = str(override.get("name", default_name))
        url = str(override.get("url", default_url))
        normalized = url.strip()
        parsed = urlparse(normalized)
        valid_url = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        enabled = bool(override.get("enabled", valid_url)) and valid_url
        result.append(CommunityLink(
            key=key,
            name=name.strip() or key,
            url=normalized if enabled else "",
            enabled=enabled,
            group="ecosystem",
            order=int(override.get("order", default_order)),
        ))
    return sorted(result, key=lambda item: item.order)


def platform_support(settings: Settings) -> PlatformSupport:
    payload = _read_content(settings.platform_content_config)
    support = payload.get("support") if isinstance(payload.get("support"), dict) else {}
    return PlatformSupport.model_validate(support or {})
