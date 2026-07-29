import enum
import uuid

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class DecisionType(str, enum.Enum):
    """§01 confidence matrix / §07 decision branching."""

    AUTO_REPLY = "auto_reply"
    DRAFT_REPLY = "draft_reply"
    ASK_CLARIFICATION = "ask_clarification"
    ROUTE = "route"
    HOLD = "hold"


class Decision(Base, UUIDPKMixin, TimestampMixin):
    """§09 ERD. `prompt_version_id` is a plain (unconstrained) reference — the
    PromptVersion table lands in increment 7; the FK constraint is added then."""

    __tablename__ = "decisions"

    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[DecisionType] = mapped_column(Enum(DecisionType, name="decision_type"), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    # Auto-reply threshold in force for the category at decision time (§01: 0.95 default) —
    # shown on the trace regardless of which band the decision landed in, so the UI can
    # show "how close" a draft/clarify/hold decision came to auto-replying.
    threshold: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.95)
    signals: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Pipeline stage timings: [{"key": "intake", "ms": 180, ...}, ...] — §09 trace shape.
    stages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    latency_ms: Mapped[int] = mapped_column(nullable=False)
    rule_overridden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    request = relationship("Request", back_populates="decisions")
    evidence = relationship("Evidence", back_populates="decision", order_by="Evidence.score.desc()")
    rule_evaluations = relationship("RuleEvaluation", back_populates="decision")


class Evidence(Base, UUIDPKMixin, TimestampMixin):
    """Citation linking a decision to a knowledge chunk (§09). Article/version/locator
    stay denormalized onto the row (rather than requiring a join through
    KnowledgeChunk -> KnowledgeVersion -> KnowledgeArticle) so the trace renders the same
    way whether or not the cited chunk still exists — evidence is an immutable record of
    what was cited at decision time, even across article edits/archival."""

    __tablename__ = "evidence"

    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("knowledge_chunks.id", ondelete="SET NULL"), nullable=True)
    retrieval_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # "vector" | "vectorless"
    score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    locator: Mapped[str] = mapped_column(String(120), nullable=False)
    article_ref: Mapped[str] = mapped_column(String(40), nullable=False)
    version_ref: Mapped[str] = mapped_column(String(20), nullable=False)

    decision = relationship("Decision", back_populates="evidence")


class RuleEvaluation(Base, UUIDPKMixin, TimestampMixin):
    """`rule_code` (e.g. "BR-022") is unconstrained until BusinessRule lands in increment 7."""

    __tablename__ = "rule_evaluations"

    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False)
    rule_code: Mapped[str] = mapped_column(String(20), nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    priority: Mapped[int] = mapped_column(nullable=False)

    decision = relationship("Decision", back_populates="rule_evaluations")
