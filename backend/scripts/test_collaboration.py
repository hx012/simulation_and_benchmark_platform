from datetime import date, datetime, timedelta, timezone
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine, select
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.analytics.models import AnalyticsEvent
from app.auth.models import User, UserSession
from app.auth.service import AuthenticatedUser
from app.collaboration.models import Demand, DemandEvent, DemandVote, FeedbackEntry, FeedbackMessage, TeamAchievementRecord
from app.collaboration.schemas import (
    DemandAdminUpdate,
    DemandCreate,
    FeedbackAdminUpdate,
    FeedbackCreate,
    TeamAchievementCreate,
    TeamAchievementRepresentativeUpdate,
    TeamAchievementScoreUpdate,
    TeamAchievementUpdate,
)
from app.collaboration.content import community_links, load_team_config, platform_support
from app.collaboration.service import (
    create_demand,
    create_feedback,
    list_demands,
    list_feedback,
    list_my_feedback,
    review_demand,
    review_feedback,
    set_vote,
    withdraw_feedback,
)
from app.collaboration.team_service import (
    create_achievement,
    delete_achievement,
    enrich_team_members,
    list_achievements,
    score_achievement,
    set_representative,
    update_achievement,
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
    AnalyticsEvent.__table__.create(engine)
    FeedbackEntry.__table__.create(engine)
    FeedbackMessage.__table__.create(engine)
    Demand.__table__.create(engine)
    DemandEvent.__table__.create(engine)
    DemandVote.__table__.create(engine)
    TeamAchievementRecord.__table__.create(engine)

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
            "  - key: jiaxian\n"
            "    name: Jiaxian From Content\n"
            "    url: https://content.example.com/jiaxian\n"
            "    enabled: true\n"
            "    order: 10\n"
            "  - key: w3\n"
            "    name: W3 From Content\n"
            "    url: https://content.example.com/w3\n"
            "    enabled: true\n"
            "    order: 20\n"
            "  - key: benchmark_wiki\n"
            "    name: Benchmark Wiki\n"
            "    url: https://content.example.com/benchmark-wiki\n"
            "    enabled: true\n"
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
        assert [link.url for link in links] == [
            "https://content.example.com/jiaxian",
            "https://content.example.com/w3",
            "https://content.example.com/benchmark-wiki",
        ]
        fallback_links = community_links(Settings(
            platform_content_config=Path(directory) / "missing-platform-content.yml",
            platform_community_jiaxian_url="https://jiaxian.example.com",
            platform_community_w3_url="https://w3.example.com",
        ))
        assert [link.url for link in fallback_links[:2]] == [
            "https://jiaxian.example.com",
            "https://w3.example.com",
        ]
        assert platform_support(settings).name == "Test Support"

        with Session(engine) as db:
            owner = User(employee_id="owner", display_name="Owner", role="normal", is_team_member=True)
            other = User(employee_id="other", display_name="Other", role="normal")
            admin = User(employee_id="admin", display_name="Admin", role="admin")
            db.add_all([owner, other, admin])
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
            assert len(list_my_feedback(db, owner_current)) == 1
            admin_current = current(owner, "admin")
            handled_feedback = review_feedback(db, feedback.feedback_id, admin_current, FeedbackAdminUpdate(
                status="processing",
                reply="已开始定位问题",
            ))
            assert handled_feedback.status == "processing"
            assert handled_feedback.messages[0].content == "已开始定位问题"
            assert len(list_feedback(db, admin_current)) == 1

            demand = create_demand(db, owner_current, DemandCreate(
                title="自动差异分析",
                domain="性能分析",
                background="当前需要人工比较结果",
                description="支持多个结果自动比较",
                business_value="减少人工回归时间",
            ))
            assert len(list_demands(db, owner_current, "mine")) == 1
            assert list_demands(db, other_current, "public") == []

            reviewed = review_demand(db, demand.id, admin_current, DemandAdminUpdate(
                status="accepted",
                visibility="public",
                priority="high",
                conclusion="纳入下一版本",
            ))
            assert reviewed.status == "accepted"
            assert reviewed.visibility == "public"
            assert reviewed.history[-1].to_status == "accepted"
            visible = list_demands(db, other_current, "public")
            assert len(visible) == 1
            assert visible[0].conclusion == "纳入下一版本"

            vote = set_vote(db, demand, other_current, True)
            assert vote.support_count == 1 and vote.voted_by_me
            vote = set_vote(db, demand, other_current, False)
            assert vote.support_count == 0 and not vote.voted_by_me

            achievement = create_achievement(db, owner_current, TeamAchievementCreate(
                title="调度模型验证",
                category="性能优化",
                summary="完成关键路径验证",
                completion_date=date(2026, 8, 18),
            ))
            assert achievement.owner_employee_id == "owner"
            assert not achievement.representative and achievement.score is None
            achievement = set_representative(
                db,
                owner_current,
                achievement.achievement_id,
                TeamAchievementRepresentativeUpdate(representative=True),
            )
            assert achievement.representative
            assert list_achievements(db, owner_current, "owner")[0].title == "调度模型验证"
            try:
                list_achievements(db, other_current, "owner")
                raise AssertionError("non-team member should not view archives")
            except HTTPException as error:
                assert error.status_code == 403
                assert error.detail == "仅团队成员可看"
            public_archive = list_achievements(db, other_current, "owner", "authenticated")
            assert public_archive[0].title == "调度模型验证"
            assert public_archive[0].can_edit is False
            assert public_archive[0].can_delete is False
            admin_current = current(admin, "admin")
            scored = score_achievement(db, admin_current, achievement.achievement_id, TeamAchievementScoreUpdate(
                score=86,
                evaluation="关键路径验证完整，成果具备较好的复用价值。",
            ))
            assert scored.score == 86
            assert scored.evaluation.startswith("关键路径验证完整")
            assert scored.scored_by_employee_id == "admin"
            assert scored.scored_at is not None
            try:
                update_achievement(db, admin_current, achievement.achievement_id, TeamAchievementUpdate(
                    title="管理员不应修改",
                    category="性能优化",
                    summary="",
                    completion_date=date(2026, 8, 18),
                ))
                raise AssertionError("admin mode should not edit member achievements")
            except HTTPException as error:
                assert error.status_code == 403
            try:
                create_achievement(db, admin_current, TeamAchievementCreate(
                    title="管理员不应代建",
                    completion_date=date(2026, 8, 20),
                ))
                raise AssertionError("admin mode should not create member achievements")
            except HTTPException as error:
                assert error.status_code == 403
            event_names = set(db.scalars(select(AnalyticsEvent.event_name)).all())
            assert {
                "team.achievement_create",
                "team.achievement_core_set",
                "team.achievement_archive_view",
                "team.achievement_score",
            }.issubset(event_names)
            score_event = db.scalar(select(AnalyticsEvent).where(
                AnalyticsEvent.event_name == "team.achievement_score"
            ))
            assert score_event is not None
            assert score_event.target_user_id == "owner"
            assert "86" in score_event.change_summary
            removable = create_achievement(db, owner_current, TeamAchievementCreate(
                title="临时成果",
                completion_date=date(2026, 8, 20),
            ))
            summary_team = SimpleNamespace(
                archive_visibility="team_only",
                viewer_is_team_member=False,
                viewer_is_admin=False,
                viewer_can_view_archives=False,
                members=[SimpleNamespace(
                    employee_id="owner",
                    is_team_member=False,
                    representative_achievements=[],
                    latest_completion_date=None,
                )],
            )
            enrich_team_members(db, owner_current, summary_team)
            assert summary_team.members[0].latest_completion_date == date(2026, 8, 18)
            set_representative(
                db,
                owner_current,
                achievement.achievement_id,
                TeamAchievementRepresentativeUpdate(representative=False),
            )
            enrich_team_members(db, owner_current, summary_team)
            assert summary_team.members[0].representative_achievements == []
            assert summary_team.members[0].latest_completion_date is None
            delete_achievement(db, owner_current, removable.achievement_id)
            assert "team.achievement_delete" in set(db.scalars(select(AnalyticsEvent.event_name)).all())
            try:
                TeamAchievementCreate(
                    title="危险链接",
                    completion_date=date(2026, 8, 19),
                    reference_url="javascript:alert(1)",
                )
                raise AssertionError("unsafe reference URL should be rejected")
            except ValueError:
                pass

            pending_feedback = create_feedback(db, other_current, FeedbackCreate(content="不再需要处理"))
            withdrawn = withdraw_feedback(db, pending_feedback.feedback_id, other_current)
            assert withdrawn.status == "withdrawn"

    print("Collaboration tests passed")


if __name__ == "__main__":
    main()
