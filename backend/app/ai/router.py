from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.pipeline import run_pipeline
from app.core.db import get_db
from app.core.permissions import Action, require_permission
from app.schemas.ai import PipelineStageOut, RunPipelineRequest, RunPipelineResponse

router = APIRouter(prefix="/v1/ai", tags=["ai"])


@router.post("/run", response_model=RunPipelineResponse)
def run_pipeline_sandbox(
    body: RunPipelineRequest,
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("decision_trace", Action.WRITE),
) -> RunPipelineResponse:
    """Staff-facing sandbox for the `AiPipelineMonitor` screen — runs the exact same
    pipeline the public portal endpoint uses, so what you see here is what customers get."""
    result = run_pipeline(db, customer_email=body.customer_email, customer_name=body.customer_name, channel=body.channel, subject=body.subject, body=body.body)
    return RunPipelineResponse(
        request_id=result.request.id,
        reference=result.request.reference,
        decision_id=result.decision.id,
        decision_type=result.decision.type.value,
        confidence=float(result.decision.confidence),
        rule_overridden=result.decision.rule_overridden,
        stages=[PipelineStageOut(key=s.key, ms=s.ms, meta=s.meta) for s in result.stages],
    )
