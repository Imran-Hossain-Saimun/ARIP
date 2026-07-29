import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class MailboxProvider(str, enum.Enum):
    MAILHOG = "mailhog"  # local dev/test — HTTP API, no real IMAP/Graph auth needed
    IMAP = "imap"
    GRAPH = "graph"


class MailboxStatus(str, enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class Mailbox(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "mailboxes"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email_address: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    provider: Mapped[MailboxProvider] = mapped_column(Enum(MailboxProvider, name="mailbox_provider"), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"))
    status: Mapped[MailboxStatus] = mapped_column(Enum(MailboxStatus, name="mailbox_status"), default=MailboxStatus.DISCONNECTED, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    department = relationship("Department")


class ParseFailure(Base, UUIDPKMixin, TimestampMixin):
    """Malformed/unparseable inbound email — logged instead of silently dropped (FR-060:
    preserve audit history even for failures the pipeline couldn't turn into a Request)."""

    __tablename__ = "parse_failures"

    mailbox_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    raw_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_from: Mapped[str | None] = mapped_column(String(320), nullable=True)
    error_message: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_source: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)

    mailbox = relationship("Mailbox")
