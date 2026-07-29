import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPKMixin:
    # sqlalchemy.Uuid (not the postgres-dialect-specific one) so the same models work
    # against SQLite in tests and native Postgres UUID in prod/dev.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


__all__ = ["Base", "UUIDPKMixin", "TimestampMixin", "utcnow"]
