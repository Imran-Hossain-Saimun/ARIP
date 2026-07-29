import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class Channel(str, enum.Enum):
    WEB = "web"
    EMAIL = "email"


class RequestStatus(str, enum.Enum):
    """§07 request lifecycle state machine."""

    RECEIVED = "received"
    PROCESSING = "processing"
    AWAITING_CUSTOMER = "awaiting_customer"
    AWAITING_APPROVAL = "awaiting_approval"
    ANSWERED = "answered"
    HELD = "held"
    ROUTED = "routed"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REOPENED = "reopened"


class Priority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Request(Base, UUIDPKMixin, TimestampMixin):
    """§09 ERD — the spine every other entity hangs off."""

    __tablename__ = "requests"

    reference: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    channel: Mapped[Channel] = mapped_column(Enum(Channel, name="channel"), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    intent: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, name="request_status"), nullable=False, default=RequestStatus.RECEIVED
    )
    priority: Mapped[Priority] = mapped_column(Enum(Priority, name="priority"), nullable=False, default=Priority.MEDIUM)
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    sla_first_response_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer")
    department = relationship("Department")
    assignee = relationship("User")
    messages = relationship("Message", back_populates="request", order_by="Message.created_at")
    attachments = relationship("Attachment", back_populates="request")
    decisions = relationship("Decision", back_populates="request", order_by="Decision.created_at")


class MessageAuthor(str, enum.Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    AI = "ai"
    SYSTEM = "system"


class Message(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "messages"

    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    author: Mapped[MessageAuthor] = mapped_column(Enum(MessageAuthor, name="message_author"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    request = relationship("Request", back_populates="messages")


class Attachment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "attachments"

    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)

    request = relationship("Request", back_populates="attachments")
