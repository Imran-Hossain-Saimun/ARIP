import base64
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import record_audit_event
from app.core.db import get_db
from app.core.idempotency import check_and_record, require_idempotency_key
from app.core.permissions import Action, enforce_department_scope, is_department_scoped, require_permission
from app.models.customer import Customer
from app.models.decision import Decision
from app.models.request import Channel, Message, MessageAuthor, Request, RequestStatus
from app.schemas.requests import (
    AssignBody,
    DecisionOut,
    EscalateBody,
    RequestCreate,
    RequestDetail,
    RequestListItem,
    RequestListResponse,
)

router = APIRouter(prefix="/v1/requests", tags=["requests"])


def _encode_cursor(created_at, row_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{created_at.isoformat()}|{row_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        created_at_str, row_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return created_at_str, row_id
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "validation_failed", "message": "Invalid cursor.", "field_errors": [], "trace_id": None},
        ) from exc


def _with_latest_confidence(req: Request) -> RequestListItem:
    item = RequestListItem.model_validate(req)
    if req.decisions:
        item.latest_confidence = float(req.decisions[-1].confidence)
    return item


@router.get("", response_model=RequestListResponse)
def list_requests(
    db: Annotated[Session, Depends(get_db)],
    current_user=require_permission("requests", Action.READ),
    status_filter: RequestStatus | None = Query(None, alias="status"),
    department_id: uuid.UUID | None = None,
    channel: Channel | None = None,
    conf_lt: float | None = None,
    cursor: str | None = None,
    limit: int = Query(50, le=200),
) -> RequestListResponse:
    stmt = select(Request).options(selectinload(Request.customer), selectinload(Request.decisions))

    if is_department_scoped(current_user.role):
        stmt = stmt.where(Request.department_id == current_user.department_id)
    elif department_id is not None:
        stmt = stmt.where(Request.department_id == department_id)

    if status_filter is not None:
        stmt = stmt.where(Request.status == status_filter)

    if channel is not None:
        stmt = stmt.where(Request.channel == channel)

    if cursor:
        created_at_str, row_id = _decode_cursor(cursor)
        cursor_dt = datetime.fromisoformat(created_at_str)
        stmt = stmt.where(
            or_(
                Request.created_at < cursor_dt,
                and_(Request.created_at == cursor_dt, Request.id < row_id),
            )
        )

    stmt = stmt.order_by(Request.created_at.desc(), Request.id.desc()).limit(limit + 1)
    rows = list(db.execute(stmt).scalars())

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [_with_latest_confidence(r) for r in rows]
    if conf_lt is not None:
        items = [i for i in items if i.latest_confidence is not None and i.latest_confidence < conf_lt]

    next_cursor = _encode_cursor(rows[-1].created_at, rows[-1].id) if has_more and rows else None
    return RequestListResponse(items=items, next_cursor=next_cursor)


@router.get("/{request_id}", response_model=RequestDetail)
def get_request(
    request_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user=require_permission("requests", Action.READ),
) -> Request:
    req = _load_request_or_404(db, request_id)
    enforce_department_scope(current_user, req.department_id)
    return req


@router.get("/{request_id}/decisions", response_model=list[DecisionOut])
def list_request_decisions(
    request_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user=require_permission("decision_trace", Action.READ),
) -> list[Decision]:
    """A request may have several decisions over its life (§09) — most recent first."""
    req = _load_request_or_404(db, request_id)
    enforce_department_scope(current_user, req.department_id)
    return sorted(req.decisions, key=lambda d: d.created_at, reverse=True)


def _load_request_or_404(db: Session, request_id: uuid.UUID) -> Request:
    stmt = (
        select(Request)
        .where(Request.id == request_id)
        .options(
            selectinload(Request.customer),
            selectinload(Request.messages),
            selectinload(Request.attachments),
            selectinload(Request.decisions).selectinload(Decision.evidence),
            selectinload(Request.decisions).selectinload(Decision.rule_evaluations),
        )
    )
    req = db.execute(stmt).scalar_one_or_none()
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Request not found.", "field_errors": [], "trace_id": None},
        )
    return req


@router.post("", response_model=RequestDetail, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: RequestCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user=require_permission("requests", Action.WRITE),
) -> Request:
    customer = db.execute(select(Customer).where(Customer.email == payload.customer_email)).scalar_one_or_none()
    if customer is None:
        customer = Customer(email=payload.customer_email, full_name=payload.customer_name)
        db.add(customer)
        db.flush()

    reference = f"REQ-{uuid.uuid4().hex[:8].upper()}"
    req = Request(reference=reference, customer_id=customer.id, channel=payload.channel, status=RequestStatus.RECEIVED)
    db.add(req)
    db.flush()

    db.add(Message(request_id=req.id, author=MessageAuthor.CUSTOMER, body=payload.body))
    record_audit_event(db, event_type="request.created", actor=current_user.email, object_ref=f"request:{req.id}", payload={"reference": reference, "channel": payload.channel.value})
    db.commit()

    return _load_request_or_404(db, req.id)


@router.patch("/{request_id}/assign", response_model=RequestDetail)
def assign_request(
    request_id: uuid.UUID,
    payload: AssignBody,
    db: Annotated[Session, Depends(get_db)],
    current_user=require_permission("reassign_escalate", Action.WRITE),
) -> Request:
    req = _load_request_or_404(db, request_id)
    enforce_department_scope(current_user, req.department_id)

    if payload.department_id is not None:
        req.department_id = payload.department_id
    if payload.assignee_id is not None:
        req.assignee_id = payload.assignee_id

    record_audit_event(
        db,
        event_type="request.assigned",
        actor=current_user.email,
        object_ref=f"request:{req.id}",
        payload={"assignee_id": str(payload.assignee_id) if payload.assignee_id else None, "department_id": str(payload.department_id) if payload.department_id else None},
    )
    db.commit()
    return _load_request_or_404(db, req.id)


@router.post("/{request_id}/approve", response_model=RequestDetail)
def approve_request(
    request_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
    current_user=require_permission("approve_send", Action.APPROVE),
) -> Request:
    req = _load_request_or_404(db, request_id)
    enforce_department_scope(current_user, req.department_id)

    if not check_and_record("approve_request", f"{idempotency_key}:{request_id}"):
        return req  # replayed request — return current state, don't re-apply the mutation

    req.status = RequestStatus.ANSWERED
    record_audit_event(db, event_type="request.approved", actor=current_user.email, object_ref=f"request:{req.id}", payload={})
    db.commit()
    return _load_request_or_404(db, req.id)


@router.post("/{request_id}/escalate", response_model=RequestDetail)
def escalate_request(
    request_id: uuid.UUID,
    payload: EscalateBody,
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
    current_user=require_permission("reassign_escalate", Action.WRITE),
) -> Request:
    req = _load_request_or_404(db, request_id)
    enforce_department_scope(current_user, req.department_id)

    if not check_and_record("escalate_request", f"{idempotency_key}:{request_id}"):
        return req

    req.status = RequestStatus.ROUTED
    record_audit_event(db, event_type="request.escalated", actor=current_user.email, object_ref=f"request:{req.id}", payload={"reason": payload.reason})
    db.commit()
    return _load_request_or_404(db, req.id)
