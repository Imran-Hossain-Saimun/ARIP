import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.permissions import Action, enforce_department_scope, require_permission
from app.models.audit import AuditEvent
from app.models.decision import Decision
from app.schemas.decisions import DecisionTrace, ReplayResult, TraceEvidence, TraceRule, TraceStage

router = APIRouter(prefix="/v1/decisions", tags=["decisions"])


def _load_decision_or_404(db: Session, decision_id: uuid.UUID) -> Decision:
    stmt = (
        select(Decision)
        .where(Decision.id == decision_id)
        .options(selectinload(Decision.request), selectinload(Decision.evidence), selectinload(Decision.rule_evaluations))
    )
    decision = db.execute(stmt).scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Decision not found.", "field_errors": [], "trace_id": None},
        )
    return decision


@router.get("/{decision_id}/trace", response_model=DecisionTrace)
def get_decision_trace(
    decision_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user=require_permission("decision_trace", Action.READ),
) -> DecisionTrace:
    decision = _load_decision_or_404(db, decision_id)
    enforce_department_scope(current_user, decision.request.department_id)

    audit_event = db.execute(select(AuditEvent).where(AuditEvent.object_ref == f"decision:{decision.id}")).scalar_one_or_none()

    return DecisionTrace(
        decision_id=str(decision.id),
        request_id=decision.request.reference,
        type=decision.type.value,
        confidence=float(decision.confidence),
        threshold=float(decision.threshold),
        signals=decision.signals,
        stages=[TraceStage(**s) for s in decision.stages],
        evidence=[
            TraceEvidence(chunk_id=str(e.chunk_id) if e.chunk_id else None, article=e.article_ref, version=e.version_ref, locator=e.locator, mode=e.retrieval_mode, score=float(e.score))
            for e in decision.evidence
        ],
        rules=[TraceRule(id=r.rule_code, outcome=r.outcome, priority=r.priority) for r in decision.rule_evaluations],
        model=decision.model,
        prompt_version=None,  # PromptVersion table lands in increment 7
        audit_hash=audit_event.hash if audit_event else None,
    )


@router.post("/{decision_id}/replay", response_model=ReplayResult)
def replay_decision(
    decision_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user=require_permission("decision_trace", Action.READ),
) -> ReplayResult:
    """Stub: the real AI pipeline (intake -> retrieval -> confidence -> rules) lands in
    increment 9. For now this confirms the decision exists and is replay-eligible, so the
    frontend's Replay action has something real to call."""
    decision = _load_decision_or_404(db, decision_id)
    enforce_department_scope(current_user, decision.request.department_id)
    return ReplayResult(decision_id=str(decision.id), replayed=False, message="Replay will re-run the live AI pipeline once increment 9 lands; today it only validates the decision is replay-eligible.")
