"""Hybrid retrieval (§08/§09): pgvector similarity ("vector" mode) + ILIKE keyword
overlap over the hierarchy-linked chunks ("vectorless" mode), fused by reciprocal-rank
fusion. Simplified vs. a production system — no cross-encoder reranking, no real
vectorless "graph traversal" beyond keyword scoring — but the non-negotiable holds
exactly: only APPROVED (or later-lifecycle) versions are ever queried, so draft
knowledge can never be cited."""

from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.providers.embeddings import EmbeddingProvider
from app.models.knowledge import KnowledgeChunk, KnowledgeVersion, KnowledgeVersionStatus

RETRIEVABLE_STATUSES = (KnowledgeVersionStatus.APPROVED, KnowledgeVersionStatus.INDEXED)
RRF_K = 60


@dataclass
class RetrievalResult:
    chunk: KnowledgeChunk
    mode: str  # "vector" | "vectorless"
    score: float


def vector_search(db: Session, query_embedding: list[float], top_k: int) -> list[tuple[KnowledgeChunk, float]]:
    # pgvector's `<=>` operator is Postgres-only. SQLite (used by the pytest fixture —
    # see conftest.py) can't run it; skip cleanly there rather than erroring, so tests
    # exercise the keyword half of hybrid search for real and the vector half stays
    # verified against the actual Postgres+pgvector container (see task doc's Delivered
    # notes for how that was done).
    if db.bind is not None and db.bind.dialect.name != "postgresql":
        return []

    distance = KnowledgeChunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(KnowledgeChunk, distance.label("distance"))
        .join(KnowledgeVersion, KnowledgeChunk.version_id == KnowledgeVersion.id)
        .where(KnowledgeVersion.status.in_(RETRIEVABLE_STATUSES))
        .order_by(distance)
        .limit(top_k)
    )
    return [(chunk, 1.0 - float(dist)) for chunk, dist in db.execute(stmt).all()]


def keyword_search(db: Session, query_text: str, top_k: int) -> list[tuple[KnowledgeChunk, float]]:
    terms = [t for t in query_text.lower().split() if len(t) > 2]
    if not terms:
        return []
    stmt = (
        select(KnowledgeChunk)
        .join(KnowledgeVersion, KnowledgeChunk.version_id == KnowledgeVersion.id)
        .where(KnowledgeVersion.status.in_(RETRIEVABLE_STATUSES))
        .where(or_(*[KnowledgeChunk.content.ilike(f"%{t}%") for t in terms]))
    )
    scored = []
    for chunk in db.execute(stmt).scalars():
        overlap = sum(1 for t in terms if t in chunk.content.lower())
        scored.append((chunk, overlap / len(terms)))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]


def hybrid_search(
    db: Session,
    query_text: str,
    embedding_provider: EmbeddingProvider,
    top_k: int = 8,
    min_score: float = 0.62,
) -> list[RetrievalResult]:
    query_embedding = embedding_provider.embed([query_text])[0]
    vector_results = vector_search(db, query_embedding, top_k)
    keyword_results = keyword_search(db, query_text, top_k)

    rrf_scores: dict[str, float] = {}
    origin: dict[str, tuple[KnowledgeChunk, str, float]] = {}
    for rank, (chunk, score) in enumerate(vector_results, start=1):
        rrf_scores[str(chunk.id)] = rrf_scores.get(str(chunk.id), 0.0) + 1.0 / (RRF_K + rank)
        origin[str(chunk.id)] = (chunk, "vector", score)
    for rank, (chunk, score) in enumerate(keyword_results, start=1):
        rrf_scores[str(chunk.id)] = rrf_scores.get(str(chunk.id), 0.0) + 1.0 / (RRF_K + rank)
        origin.setdefault(str(chunk.id), (chunk, "vectorless", score))

    ranked_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)
    results = [RetrievalResult(chunk=origin[cid][0], mode=origin[cid][1], score=origin[cid][2]) for cid in ranked_ids]
    return [r for r in results if r.score >= min_score][:top_k]
