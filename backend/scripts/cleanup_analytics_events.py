"""Delete raw analytics events beyond the configured retention period."""

import os
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

from app.analytics.service import delete_expired_events  # noqa: E402
from app.common.config import get_settings  # noqa: E402
from app.common.database import SessionLocal  # noqa: E402


def main() -> None:
    retention_days = get_settings().analytics_event_retention_days
    if retention_days == 0:
        print("analytics_event_cleanup=disabled")
        return

    with SessionLocal.begin() as db:
        deleted = delete_expired_events(db, retention_days)

    print(
        f"analytics_event_cleanup=complete "
        f"deleted={deleted} retention_days={retention_days}"
    )


if __name__ == "__main__":
    main()
