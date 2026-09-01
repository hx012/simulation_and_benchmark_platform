from datetime import date
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.collaboration.content import load_feature_releases
from app.common.config import Settings


def main() -> None:
    with TemporaryDirectory() as directory:
        config_path = Path(directory) / "platform_content.yml"
        config_path.write_text(
            "feature_releases:\n"
            "  enabled: true\n"
            "  max_items: 2\n"
            "  new_badge_days: 10\n"
            "  items:\n"
            "    - id: older\n"
            "      title: Older feature\n"
            "      launched_at: '2026-07-01'\n"
            "      action_url: https://example.com/feature\n"
            "    - id: latest\n"
            "      title: Latest feature\n"
            "      launched_at: '2026-08-20'\n"
            "      action_url: /performance\n"
            "    - id: unsafe-url\n"
            "      title: Unsafe URL\n"
            "      launched_at: '2026-06-01'\n"
            "      action_url: javascript:alert(1)\n"
            "    - id: future\n"
            "      title: Future feature\n"
            "      launched_at: '2026-09-01'\n"
            "    - id: hidden\n"
            "      title: Hidden feature\n"
            "      launched_at: '2026-08-25'\n"
            "      enabled: false\n",
            encoding="utf-8",
        )

        releases = load_feature_releases(
            Settings(platform_content_config=config_path),
            today=date(2026, 8, 27),
        )
        assert releases.max_items == 2
        assert releases.new_badge_days == 10
        assert [item.id for item in releases.items] == ["latest", "older", "unsafe-url"]
        assert releases.items[0].action_url == "/performance"
        assert releases.items[1].action_url == "https://example.com/feature"
        assert releases.items[-1].action_url == ""

        config_path.write_text("feature_releases:\n  enabled: false\n", encoding="utf-8")
        disabled = load_feature_releases(Settings(platform_content_config=config_path))
        assert not disabled.enabled
        assert disabled.items == []

    print("Feature release tests passed")


if __name__ == "__main__":
    main()
