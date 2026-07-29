import enum
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin

EMBEDDING_DIM = 1536


class KnowledgeVersionStatus(str, enum.Enum):
    """§03 lifecycle: Draft -> Review -> Approved -> Indexed -> Available to AI -> Archived.
    We collapse "Approved" and "Available to AI" into one: a version is queryable by the
    retrieval pipeline the instant it's APPROVED (see knowledge/retrieval.py) — INDEXED
    just means the embed/chunk background job has finished, it isn't a separate gate."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    INDEXED = "indexed"
    ARCHIVED = "archived"


class AccessLevel(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


class KnowledgeArticle(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "knowledge_articles"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"))
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    department = relationship("Department")
    versions = relationship("KnowledgeVersion", back_populates="article", order_by="KnowledgeVersion.created_at.desc()")


class KnowledgeVersion(Base, UUIDPKMixin, TimestampMixin):
    """§09 explicit fields: version, status, effective_from, expires_on, access_level,
    indexed_at. `content` is the extracted plain text this version was chunked from."""

    __tablename__ = "knowledge_versions"

    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_articles.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[KnowledgeVersionStatus] = mapped_column(Enum(KnowledgeVersionStatus, name="knowledge_version_status"), default=KnowledgeVersionStatus.DRAFT, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    access_level: Mapped[AccessLevel] = mapped_column(Enum(AccessLevel, name="access_level"), default=AccessLevel.INTERNAL, nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    article = relationship("KnowledgeArticle", back_populates="versions")
    chunks = relationship("KnowledgeChunk", back_populates="version", cascade="all, delete-orphan")
    nodes = relationship("KnowledgeNode", back_populates="version", cascade="all, delete-orphan")


class KnowledgeNode(Base, UUIDPKMixin, TimestampMixin):
    """Hierarchy tree for "vectorless" retrieval (§08/§09) — one tree per version."""

    __tablename__ = "knowledge_nodes"

    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_versions.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("knowledge_nodes.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    locator: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. "§3.1"
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    version = relationship("KnowledgeVersion", back_populates="nodes")


class KnowledgeChunk(Base, UUIDPKMixin, TimestampMixin):
    """§09: chunk_size 800 / overlap 120 (approximated in words, not a real tokenizer —
    see knowledge/chunking.py)."""

    __tablename__ = "knowledge_chunks"

    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_versions.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("knowledge_nodes.id", ondelete="SET NULL"), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)

    version = relationship("KnowledgeVersion", back_populates="chunks")
    node = relationship("KnowledgeNode")


class KnowledgeGapStatus(str, enum.Enum):
    OPEN = "open"
    DRAFTING = "drafting"
    CLOSED = "closed"


class KnowledgeGap(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "knowledge_gaps"

    cluster_key: Mapped[str] = mapped_column(String(120), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    status: Mapped[KnowledgeGapStatus] = mapped_column(Enum(KnowledgeGapStatus, name="knowledge_gap_status"), default=KnowledgeGapStatus.OPEN, nullable=False)
    sample_request_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
