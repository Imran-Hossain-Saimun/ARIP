import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.knowledge import AccessLevel, KnowledgeGapStatus, KnowledgeVersionStatus


class KnowledgeVersionOut(BaseModel):
    id: uuid.UUID
    version: str
    status: KnowledgeVersionStatus
    effective_from: date
    expires_on: date | None
    access_level: AccessLevel
    indexed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeArticleListItem(BaseModel):
    id: uuid.UUID
    title: str
    department_id: uuid.UUID | None
    category: str | None
    tags: list[str]
    latest_version: KnowledgeVersionOut | None

    model_config = {"from_attributes": True}


class KnowledgeArticleDetail(KnowledgeArticleListItem):
    versions: list[KnowledgeVersionOut]


class KnowledgeIngestResponse(BaseModel):
    article_id: uuid.UUID
    version_id: uuid.UUID
    chunk_count: int
    node_count: int


class VersionApproveBody(BaseModel):
    effective_from: date | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 8
    min_score: float = 0.62


class SearchResultItem(BaseModel):
    chunk_id: uuid.UUID
    article_id: uuid.UUID
    article_title: str
    version: str
    locator: str
    mode: str
    score: float
    content: str


class KnowledgeGapOut(BaseModel):
    id: uuid.UUID
    cluster_key: str
    occurrence_count: int
    avg_confidence: float
    status: KnowledgeGapStatus
    sample_request_refs: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
