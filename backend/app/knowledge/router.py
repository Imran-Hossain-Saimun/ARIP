import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.providers.embeddings import get_embedding_provider
from app.core.audit import record_audit_event
from app.core.db import get_db
from app.core.permissions import Action, require_permission
from app.core.security import CurrentUser
from app.core.storage import upload_document
from app.knowledge.ingestion import index_version
from app.knowledge.retrieval import hybrid_search
from app.models.knowledge import (
    AccessLevel,
    KnowledgeArticle,
    KnowledgeGap,
    KnowledgeVersion,
    KnowledgeVersionStatus,
)
from app.schemas.knowledge import (
    KnowledgeArticleDetail,
    KnowledgeArticleListItem,
    KnowledgeGapOut,
    KnowledgeIngestResponse,
    KnowledgeVersionOut,
    SearchRequest,
    SearchResultItem,
    VersionApproveBody,
)

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])
gaps_router = APIRouter(prefix="/v1/gaps", tags=["knowledge-gaps"])


def _to_list_item(article: KnowledgeArticle) -> KnowledgeArticleListItem:
    latest = article.versions[0] if article.versions else None
    return KnowledgeArticleListItem(
        id=article.id,
        title=article.title,
        department_id=article.department_id,
        category=article.category,
        tags=article.tags,
        latest_version=KnowledgeVersionOut.model_validate(latest) if latest else None,
    )


@router.get("", response_model=list[KnowledgeArticleListItem])
def list_knowledge(
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("knowledge_authoring", Action.READ),
    status_filter: KnowledgeVersionStatus | None = Query(None, alias="status"),
    department_id: uuid.UUID | None = None,
    q: str | None = None,
) -> list[KnowledgeArticleListItem]:
    stmt = select(KnowledgeArticle).options(selectinload(KnowledgeArticle.versions))
    if department_id is not None:
        stmt = stmt.where(KnowledgeArticle.department_id == department_id)
    if q:
        stmt = stmt.where(KnowledgeArticle.title.ilike(f"%{q}%"))

    articles = list(db.execute(stmt).scalars())
    items = [_to_list_item(a) for a in articles]
    if status_filter is not None:
        items = [i for i in items if i.latest_version and i.latest_version.status == status_filter]
    return items


@router.get("/{article_id}", response_model=KnowledgeArticleDetail)
def get_knowledge_article(
    article_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("knowledge_authoring", Action.READ),
) -> KnowledgeArticleDetail:
    stmt = select(KnowledgeArticle).where(KnowledgeArticle.id == article_id).options(selectinload(KnowledgeArticle.versions))
    article = db.execute(stmt).scalar_one_or_none()
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Knowledge article not found.", "field_errors": [], "trace_id": None})
    item = _to_list_item(article)
    return KnowledgeArticleDetail(**item.model_dump(), versions=[KnowledgeVersionOut.model_validate(v) for v in article.versions])


@router.post("/ingest", response_model=KnowledgeIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_knowledge(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, require_permission("knowledge_authoring", Action.WRITE)],
    title: Annotated[str, Form()],
    version: Annotated[str, Form()] = "v1.0",
    department_id: Annotated[uuid.UUID | None, Form()] = None,
    category: Annotated[str | None, Form()] = None,
    access_level: Annotated[AccessLevel, Form()] = AccessLevel.INTERNAL,
    effective_from: Annotated[date | None, Form()] = None,
    content: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> KnowledgeIngestResponse:
    """Real text (.txt/.md) is parsed directly from the uploaded file. Binary formats
    (PDF/DOCX/XLSX from §09's supported-sources list) aren't parsed in this pass — pass
    their pre-extracted text via the `content` field instead; the file, if given, is
    still stored as-is in object storage for reference."""
    storage_key = None
    text = content or ""

    if file is not None:
        raw = await file.read()
        storage_key = upload_document(file.filename or "upload.bin", raw, file.content_type or "application/octet-stream")
        if not text and (file.filename or "").lower().endswith((".txt", ".md")):
            text = raw.decode("utf-8", errors="replace")

    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "validation_failed", "message": "No text content — provide `content` or a .txt/.md file.", "field_errors": [], "trace_id": None},
        )

    article = KnowledgeArticle(title=title, department_id=department_id, category=category, tags=[])
    db.add(article)
    db.flush()

    kv = KnowledgeVersion(
        article_id=article.id,
        version=version,
        status=KnowledgeVersionStatus.DRAFT,
        effective_from=effective_from or date.today(),
        access_level=access_level,
        content=text,
        storage_key=storage_key,
    )
    db.add(kv)
    db.flush()

    record_audit_event(db, event_type="knowledge.ingested", actor=current_user.email, object_ref=f"knowledge_version:{kv.id}", payload={"article_id": str(article.id), "version": version})
    db.commit()

    return KnowledgeIngestResponse(article_id=article.id, version_id=kv.id, chunk_count=0, node_count=0)


@router.post("/{article_id}/versions/{version}/approve", response_model=KnowledgeVersionOut)
def approve_knowledge_version(
    article_id: uuid.UUID,
    version: str,
    body: VersionApproveBody,
    db: Annotated[Session, Depends(get_db)],
    current_user=require_permission("knowledge_approval", Action.APPROVE),
) -> KnowledgeVersion:
    """§13 non-negotiable: draft knowledge can never reach the retrieval result set — this
    is the ONLY place a version's chunks get embedded/indexed, and it only runs once the
    version leaves Draft/Review."""
    kv = db.execute(
        select(KnowledgeVersion).where(KnowledgeVersion.article_id == article_id, KnowledgeVersion.version == version)
    ).scalar_one_or_none()
    if kv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Knowledge version not found.", "field_errors": [], "trace_id": None})

    kv.status = KnowledgeVersionStatus.APPROVED
    kv.reviewer_id = current_user.id
    if body.effective_from:
        kv.effective_from = body.effective_from

    index_version(db, kv, get_embedding_provider())
    kv.status = KnowledgeVersionStatus.INDEXED

    record_audit_event(db, event_type="knowledge.approved", actor=current_user.email, object_ref=f"knowledge_version:{kv.id}", payload={"version": version})
    db.commit()
    db.refresh(kv)
    return kv


@router.post("/search", response_model=list[SearchResultItem])
def search_knowledge(
    body: SearchRequest,
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("knowledge_authoring", Action.READ),
) -> list[SearchResultItem]:
    results = hybrid_search(db, body.query, get_embedding_provider(), top_k=body.top_k, min_score=body.min_score)
    out = []
    for r in results:
        version = r.chunk.version
        out.append(
            SearchResultItem(
                chunk_id=r.chunk.id,
                article_id=version.article_id,
                article_title=version.article.title,
                version=version.version,
                locator=r.chunk.node.locator if r.chunk.node else "§1",
                mode=r.mode,
                score=r.score,
                content=r.chunk.content[:400],
            )
        )
    return out


@gaps_router.get("", response_model=list[KnowledgeGapOut])
def list_knowledge_gaps(
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("knowledge_authoring", Action.READ),
) -> list[KnowledgeGap]:
    stmt = select(KnowledgeGap).order_by(KnowledgeGap.occurrence_count.desc())
    return list(db.execute(stmt).scalars())
