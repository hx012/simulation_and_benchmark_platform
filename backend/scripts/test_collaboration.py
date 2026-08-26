from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth.models import User, UserSession
from app.auth.service import AuthenticatedUser
from app.collaboration.models import Demand, DemandVote, FeedbackEntry
from app.collaboration.schemas import DemandCreate, FeedbackCreate
from app.collaboration.content import community_links, load_team_config, platform_support
from app.collaboration.service import (
    create_demand,
    create_feedback,
    list_demands,
    list_feedback,
    set_vote,
)
from app.common.config import Settings


def current(user: User, auth_mode: str = "normal") -> AuthenticatedUser:
    now = datetime.now(timezone.utc)
    return AuthenticatedUser(
        user=user,
        session=UserSession(
            user_id=user.id,
            token_hash=f"token-{user.employee_id}",
            auth_mode=auth_mode,
            expires_at=now + timedelta(hours=1),
            last_seen_at=now,
        ),
    )


def main() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    User.__table__.create(engine)
    FeedbackEntry.__table__.create(engine)
    Demand.__table__.create(engine)
    DemandVote.__table__.create(engine)

    with TemporaryDirectory() as directory:
        config_path = Path(directory) / "platform_content.yml"
        extra_members = "".join(
            "    - employee_id: extra-{index}\n"
            "      name: Extra {index}\n"
            "      order: {order}\n"
            "      enabled: true\n".format(index=index, order=20 + index)
            for index in range(1, 9)
        )
        config_path.write_text(
            "team:\n"
            "  name: Test Team\n"
            "  description: Config driven\n"
            "  members:\n"
            "    - employee_id: h2\n"
            "      name: Two\n"
            "      tags: [Trace, Tooling]\n"
            "      order: 20\n"
            "      enabled: true\n"
            "    - employee_id: h1\n"
            "      name: One\n"
            "      order: 10\n"
            "      enabled: true\n"
            "    - employee_id: hidden\n"
            "      name: Hidden\n"
            "      enabled: false\n"
            + extra_members
            + "  achievements:\n"
            "    - id: featured\n"
            "      title: Featured\n"
            "      featured: true\n"
            "      featured_order: 10\n"
            "      enabled: true\n"
            "communities:\n"
            "  - key: benchmark_wiki\n"
            "    name: Benchmark Wiki\n"
            "    enabled: false\n"
            "    order: 30\n"
            "support:\n"
            "  name: Test Support\n"
            "demand_reviews: {}\n",
            encoding="utf-8",
        )
        settings = Settings(
            platform_content_config=config_path,
            platform_community_jiaxian_url="https://jiaxian.example.com",
            platform_community_w3_url="https://w3.example.com",
        )
        team = load_team_config(settings)
        assert [member.employee_id for member in team.members] == [
            "h1", "h2", *(f"extra-{index}" for index in range(1, 9)),
        ]
        assert team.members[1].tags == ["Trace", "Tooling"]
        assert team.achievements[0].featured
        links = community_links(settings)
        assert [link.key for link in links] == ["jiaxian", "w3", "benchmark_wiki"]
        assert links[0].enabled and not links[-1].enabled
        assert platform_support(settings).name == "Test Support"

        with Session(engine) as db:
            owner = User(employee_id="owner", display_name="Owner", role="normal")
            other = User(employee_id="other", display_name="Other", role="normal")
            db.add_all([owner, other])
            db.commit()

            owner_current = current(owner)
            other_current = current(other)
            feedback = create_feedback(db, owner_current, FeedbackCreate(
                feedback_type="experience",
                page_title="首页",
                page_path="/home",
                content="希望交互更清晰",
            ))
            assert feedback.user_id == "owner"
            assert len(list_feedback(db)) == 1

            demand = create_demand(db, owner_current, DemandCreate(
                title="自动差异分析",
                domain="性能分析",
                background="当前需要人工比较结果",
                description="支持多个结果自动比较",
                business_value="减少人工回归时间",
            ))
            assert len(list_demands(db, owner_current, settings)) == 1
            assert list_demands(db, other_current, settings) == []

            vote = set_vote(db, demand, owner_current, True)
            assert vote.support_count == 1 and vote.voted_by_me
            vote = set_vote(db, demand, owner_current, False)
            assert vote.support_count == 0 and not vote.voted_by_me

            config_path.write_text(
                "team: {}\ndemand_reviews:\n"
                f"  {demand.request_no}:\n"
                "    visibility: public\n"
                "    status: accepted\n"
                "    conclusion: 已采纳\n",
                encoding="utf-8",
            )
            visible = list_demands(db, other_current, settings)
            assert len(visible) == 1
            assert visible[0].status == "accepted"
            assert visible[0].conclusion == "已采纳"

    print("Collaboration tests passed")


if __name__ == "__main__":
    main()
