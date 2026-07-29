from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.pipeline import run_pipeline
from app.core.audit import record_audit_event
from app.core.db import get_db
from app.models.customer import Customer
from app.models.decision import Decision
from app.models.feedback import Feedback
from app.models.request import Channel, MessageAuthor, Request, RequestStatus
from app.schemas.portal import (
    PortalFeedbackRequest,
    PortalMessageOut,
    PortalSubmitRequest,
    PortalSubmitResponse,
    PortalTrackResponse,
)

router = APIRouter(prefix="/v1/portal", tags=["portal"])

# §07: Received -> Reviewed -> Preparing answer -> Resolved
_PROGRESS_STAGE = {
    RequestStatus.RECEIVED: "Received",
    RequestStatus.PROCESSING: "Reviewed",
    RequestStatus.AWAITING_CUSTOMER: "Preparing answer",
    RequestStatus.AWAITING_APPROVAL: "Preparing answer",
    RequestStatus.HELD: "Preparing answer",
    RequestStatus.ROUTED: "Preparing answer",
    RequestStatus.IN_PROGRESS: "Preparing answer",
    RequestStatus.REOPENED: "Preparing answer",
    RequestStatus.ANSWERED: "Resolved",
    RequestStatus.RESOLVED: "Resolved",
}


def _load_by_reference_and_email(db: Session, reference: str, email: str) -> Request:
    stmt = (
        select(Request)
        .join(Customer, Request.customer_id == Customer.id)
        .where(Request.reference == reference, Customer.email == email)
        .options(selectinload(Request.messages), selectinload(Request.customer))
    )
    request = db.execute(stmt).scalar_one_or_none()
    if request is None:
        # Deliberately the same 404 whether the reference or the email is wrong — don't
        # leak which one was correct to an unauthenticated caller.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "No request found for that reference and email.", "field_errors": [], "trace_id": None})
    return request


@router.post("/requests", response_model=PortalSubmitResponse, status_code=status.HTTP_201_CREATED)
def submit_request(body: PortalSubmitRequest, db: Annotated[Session, Depends(get_db)]) -> PortalSubmitResponse:
    """No staff RBAC gate — this is the public-facing intake endpoint (FR-001/FR-002).
    Runs the full AI pipeline synchronously so the customer gets an immediate answer or
    an honest "we're routing this" response, matching §07's customer journey."""
    result = run_pipeline(db, customer_email=body.customer_email, customer_name=body.customer_name, channel=Channel.WEB, subject=body.subject, body=body.body)

    db.refresh(result.request, attribute_names=["messages"])
    ai_message = next((m.body for m in result.request.messages if m.author == MessageAuthor.AI), None)
    citations = [e.article_ref for e in result.decision.evidence] if result.decision.type.value in ("auto_reply", "draft_reply") else []

    return PortalSubmitResponse(
        reference=result.request.reference,
        status=result.request.status.value,
        progress_stage=_PROGRESS_STAGE[result.request.status],
        ai_message=ai_message,
        citations=citations,
    )


@router.get("/requests/{reference}", response_model=PortalTrackResponse)
def track_request(reference: str, email: str, db: Annotated[Session, Depends(get_db)]) -> PortalTrackResponse:
    request = _load_by_reference_and_email(db, reference, email)
    return PortalTrackResponse(
        reference=request.reference,
        status=request.status.value,
        progress_stage=_PROGRESS_STAGE[request.status],
        channel=request.channel,
        messages=[PortalMessageOut(author=m.author.value, body=m.body) for m in request.messages],
    )


@router.post("/requests/{reference}/feedback", status_code=status.HTTP_201_CREATED)
def submit_feedback(reference: str, body: PortalFeedbackRequest, db: Annotated[Session, Depends(get_db)]) -> dict:
    request = _load_by_reference_and_email(db, reference, body.email)
    if request.status not in (RequestStatus.ANSWERED, RequestStatus.RESOLVED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "validation_failed", "message": "Feedback can only be left once a request is resolved.", "field_errors": [], "trace_id": None})
    if not 1 <= body.rating <= 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "validation_failed", "message": "Rating must be between 1 and 5.", "field_errors": [{"loc": ["rating"], "msg": "out of range"}], "trace_id": None})

    db.add(Feedback(request_id=request.id, rating=body.rating, comment=body.comment))
    record_audit_event(db, event_type="feedback.submitted", actor=body.email, object_ref=f"request:{request.id}", payload={"rating": body.rating})
    db.commit()
    return {"ok": True}
