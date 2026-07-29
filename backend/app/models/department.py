from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class Department(Base, UUIDPKMixin, TimestampMixin):
    """§12 RBAC department isolation (FR-063) scopes rows to one of these."""

    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
