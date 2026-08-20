from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.simulation.enums import UploadSessionStatus
from app.simulation.models import UploadSession


class UploadSessionRepository:
    def create(
        self,
        db: Session,
        upload_session: UploadSession,
    ) -> UploadSession:
        db.add(upload_session)
        db.flush()
        db.refresh(upload_session)
        return upload_session

    def get(
        self,
        db: Session,
        upload_session_id: str,
    ) -> UploadSession | None:
        stmt = (
            select(UploadSession)
            .where(
                UploadSession.upload_session_id
                == upload_session_id
            )
        )
        return db.scalar(stmt)

    def get_for_update(
        self,
        db: Session,
        upload_session_id: str,
    ) -> UploadSession | None:
        stmt = (
            select(UploadSession)
            .where(
                UploadSession.upload_session_id
                == upload_session_id
            )
            .with_for_update()
        )
        return db.scalar(stmt)

    def list_stale_sessions(
        self,
        db: Session,
        *,
        cutoff: datetime,
        limit: int,
    ) -> list[UploadSession]:
        stmt = (
            select(UploadSession)
            .where(
                UploadSession.status.notin_(
                    [
                        UploadSessionStatus.SUBMITTED,
                        UploadSessionStatus.EXPIRED,
                    ]
                ),
                UploadSession.last_activity_at < cutoff,
            )
            .order_by(UploadSession.last_activity_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        return list(db.scalars(stmt).all())


    def count_committing_for_owner(
        self,
        db: Session,
        owner_id: str,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(UploadSession)
            .where(
                UploadSession.owner_id == owner_id,
                UploadSession.status == UploadSessionStatus.COMMITTING,
                UploadSession.submitted_task_id.is_not(None),
            )
        )
        return int(db.scalar(stmt) or 0)

    def delete_by_submitted_task_id(
        self,
        db: Session,
        task_id: str,
    ) -> None:
        stmt = (
            select(UploadSession)
            .where(UploadSession.submitted_task_id == task_id)
            .with_for_update()
        )
        upload_session = db.scalar(stmt)
        if upload_session is not None:
            db.delete(upload_session)
            db.flush()

    def save(
        self,
        db: Session,
        upload_session: UploadSession,
    ) -> UploadSession:
        db.add(upload_session)
        db.flush()
        return upload_session
