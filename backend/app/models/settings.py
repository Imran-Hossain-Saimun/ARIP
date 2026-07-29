from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import utcnow


class AppSetting(Base):
    """Simple key-value org settings — AI provider config, retrieval knobs, webhook
    endpoints. Unlike ConfigResource these aren't versioned/approvable; they're plain
    admin-tunable values (§10 Settings screens: AI providers, retrieval config)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
