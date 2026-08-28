from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


def new_id() -> str:
    return str(uuid4())


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    page_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    result: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    active_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    vendor: Mapped[str | None] = mapped_column(String(128))
    chip: Mapped[str | None] = mapped_column(String(128))
    benchmark_name: Mapped[str | None] = mapped_column(String(255))
    benchmark_type: Mapped[str | None] = mapped_column(String(64))
    test_target: Mapped[str | None] = mapped_column(String(128))
    simulator_version: Mapped[str | None] = mapped_column(String(128))
    chip_variant: Mapped[str | None] = mapped_column(String(128))
    simulation_mode: Mapped[str | None] = mapped_column(String(64))
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(512))
    target_name: Mapped[str | None] = mapped_column(String(255))
    target_user_id: Mapped[str | None] = mapped_column(String(128))
    auth_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    change_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("event_id", name="uq_analytics_events_event_id"),
        Index("ix_analytics_events_occurred", "occurred_at"),
        Index("ix_analytics_events_user_occurred", "user_id", "occurred_at"),
        Index("ix_analytics_events_page_occurred", "page_key", "occurred_at"),
        Index("ix_analytics_events_name_occurred", "event_name", "occurred_at"),
        Index("ix_analytics_events_chip_occurred", "chip", "occurred_at"),
        Index("ix_analytics_events_benchmark_occurred", "benchmark_name", "occurred_at"),
    )
