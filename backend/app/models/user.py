import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class RoleName(str, enum.Enum):
    """§12 RBAC matrix roles — enforced server-side, never a UI-only gate."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    KNOWLEDGE_MANAGER = "knowledge_manager"
    DEPT_MANAGER = "dept_manager"
    SUPPORT_AGENT = "support_agent"
    EXECUTIVE = "executive"
    AUDITOR = "auditor"
    CUSTOMER = "customer"


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[RoleName] = mapped_column(Enum(RoleName, name="role_name"), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    department = relationship("Department")
