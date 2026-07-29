import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class ConfigResourceKind(str, enum.Enum):
    """The four automation surfaces (§13 increment 7) — one table, one lifecycle,
    reused four times rather than four near-identical tables/routers."""

    WORKFLOW = "workflow"
    BUSINESS_RULE = "business_rule"
    PROMPT_TEMPLATE = "prompt_template"
    ROUTING_RULE = "routing_rule"


class ConfigResourceStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ConfigResource(Base, UUIDPKMixin, TimestampMixin):
    """Versioned config, shared across workflows/business rules/prompts/routing rules.
    `key` identifies the logical resource (e.g. "BR-022", "reply_draft_prompt",
    "cards_dispute_workflow"); each edit is a new row with an incremented `version` under
    the same (kind, key) — never an in-place update, so publish/rollback just flips which
    version is ACTIVE. `config` holds the kind-specific payload (rule WHEN/THEN, prompt
    text+model params, workflow node graph, routing matrix entry)."""

    __tablename__ = "config_resources"

    kind: Mapped[ConfigResourceKind] = mapped_column(Enum(ConfigResourceKind, name="config_resource_kind"), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[ConfigResourceStatus] = mapped_column(Enum(ConfigResourceStatus, name="config_resource_status"), default=ConfigResourceStatus.DRAFT, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator = relationship("User")


class WorkflowRunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class WorkflowRun(Base, UUIDPKMixin, TimestampMixin):
    """Execution history for a workflow definition. Runs are seeded/recorded here but
    there is no live execution engine in this build (see task doc's Delivered notes) —
    a real engine would create these rows as workflows actually fire on decisions."""

    __tablename__ = "workflow_runs"

    workflow_key: Mapped[str] = mapped_column(String(120), nullable=False)
    request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("requests.id", ondelete="SET NULL"))
    status: Mapped[WorkflowRunStatus] = mapped_column(Enum(WorkflowRunStatus, name="workflow_run_status"), default=WorkflowRunStatus.RUNNING, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    actions = relationship("WorkflowAction", back_populates="run", order_by="WorkflowAction.executed_at")


class WorkflowActionStatus(str, enum.Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRIED = "retried"


class WorkflowAction(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "workflow_actions"

    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[WorkflowActionStatus] = mapped_column(Enum(WorkflowActionStatus, name="workflow_action_status"), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run = relationship("WorkflowRun", back_populates="actions")
