import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.permissions import Action, require_permission
from app.email.sync import sync_mailbox
from app.models.email import Mailbox, ParseFailure
from app.schemas.email import MailboxCreate, MailboxOut, ParseFailureOut, SyncResult

router = APIRouter(prefix="/v1/email", tags=["email"])


@router.get("/mailboxes", response_model=list[MailboxOut])
def list_mailboxes(
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("email", Action.READ),
) -> list[Mailbox]:
    return list(db.execute(select(Mailbox).order_by(Mailbox.name)).scalars())


@router.post("/mailboxes", response_model=MailboxOut, status_code=status.HTTP_201_CREATED)
def create_mailbox(
    body: MailboxCreate,
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("email", Action.WRITE),
) -> Mailbox:
    mailbox = Mailbox(name=body.name, email_address=body.email_address, provider=body.provider, department_id=body.department_id)
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)
    return mailbox


@router.post("/mailboxes/{mailbox_id}/sync", response_model=SyncResult)
def sync_mailbox_now(
    mailbox_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("email", Action.WRITE),
) -> dict:
    mailbox = db.get(Mailbox, mailbox_id)
    if mailbox is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Mailbox not found.", "field_errors": [], "trace_id": None})
    try:
        return sync_mailbox(db, mailbox)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "provider_not_supported", "message": str(exc), "field_errors": [], "trace_id": None},
        ) from exc


@router.get("/parse-failures", response_model=list[ParseFailureOut])
def list_parse_failures(
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("email", Action.READ),
    resolved: bool | None = None,
) -> list[ParseFailure]:
    stmt = select(ParseFailure).order_by(ParseFailure.created_at.desc())
    if resolved is not None:
        stmt = stmt.where(ParseFailure.resolved == resolved)
    return list(db.execute(stmt).scalars())


@router.post("/parse-failures/{failure_id}/resolve", response_model=ParseFailureOut)
def resolve_parse_failure(
    failure_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("email", Action.WRITE),
) -> ParseFailure:
    failure = db.get(ParseFailure, failure_id)
    if failure is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Parse failure not found.", "field_errors": [], "trace_id": None})
    failure.resolved = True
    db.commit()
    db.refresh(failure)
    return failure
