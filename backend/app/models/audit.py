from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import UUIDPKMixin, utcnow


class AuditEvent(Base, UUIDPKMixin):
    """§09 — append-only, sha256 hash-chained. Never updated or deleted; see
    app/core/audit.py for the only sanctioned way to insert a row."""

    __tablename__ = "audit_events"

    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(320), nullable=False)
    object_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    prev_hash: Mapped[str | None] = mapped_column(String(71), nullable=True)  # "sha256:" + 64 hex chars
    hash: Mapped[str] = mapped_column(String(71), nullable=False, unique=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
