from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import verify_chain
from app.core.db import get_db
from app.core.permissions import Action, require_permission
from app.models.audit import AuditEvent
from app.schemas.audit import AuditEventOut, ChainVerifyResult

router = APIRouter(prefix="/v1/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventOut])
def list_audit_events(
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("audit_logs", Action.READ),
    event_type: str | None = Query(None, alias="type"),
    actor: str | None = None,
    object_ref: str | None = Query(None, alias="object"),
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
    limit: int = Query(100, le=500),
) -> list[AuditEvent]:
    stmt = select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(limit)
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if actor:
        stmt = stmt.where(AuditEvent.actor == actor)
    if object_ref:
        stmt = stmt.where(AuditEvent.object_ref == object_ref)
    if date_from:
        stmt = stmt.where(AuditEvent.occurred_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditEvent.occurred_at <= date_to)
    return list(db.execute(stmt).scalars())


@router.get("/verify", response_model=ChainVerifyResult)
def verify_audit_chain(db: Annotated[Session, Depends(get_db)], _user=require_permission("audit_logs", Action.READ)) -> ChainVerifyResult:
    """§13 E2E target: confirm the exported/stored hash chain hasn't been tampered with."""
    valid, count, broken_at = verify_chain(db)
    return ChainVerifyResult(valid=valid, event_count=count, broken_at_id=broken_at)


@router.get("/export", response_model=list[AuditEventOut])
def export_audit_events(db: Annotated[Session, Depends(get_db)], _user=require_permission("audit_logs", Action.READ)) -> list[AuditEvent]:
    """Full, unpaginated export — small enough for this build's data volume; a real
    deployment would stream this rather than load it all into memory."""
    return list(db.execute(select(AuditEvent).order_by(AuditEvent.occurred_at)).scalars())
