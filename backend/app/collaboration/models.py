from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


def new_id() -> str:
    return str(uuid4())


class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)
    page_title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    page_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_feedback_entries_created", "created_at"),)


class Demand(Base):
    __tablename__ = "demands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    request_no: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_time: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    background: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    business_value: Mapped[str] = mapped_column(Text, nullable=False)
    contact: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_demands_user_created", "user_id", "created_at"),
        Index("ix_demands_domain_created", "domain", "created_at"),
    )


class DemandVote(Base):
    __tablename__ = "demand_votes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    demand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("demands.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("demand_id", "user_id", name="uq_demand_vote"),
        Index("ix_demand_votes_demand", "demand_id"),
    )
