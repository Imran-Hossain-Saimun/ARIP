import uuid

from sqlalchemy import ForeignKey, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class Feedback(Base, UUIDPKMixin, TimestampMixin):
    """Customer CSAT rating (FR-085), feeds knowledge-gap/prompt-eval signals (§03)."""

    __tablename__ = "feedback"

    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1-5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    request = relationship("Request")
