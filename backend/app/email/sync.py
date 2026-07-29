import json
import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.email.mailhog_client import InboundMessage, delete_message, fetch_messages
from app.models.base import utcnow
from app.models.customer import Customer
from app.models.email import Mailbox, MailboxProvider, MailboxStatus, ParseFailure
from app.models.request import Channel, Message, MessageAuthor, Request, RequestStatus

REFERENCE_RE = re.compile(r"REQ-[A-Z0-9]+", re.IGNORECASE)


def sync_mailbox(db: Session, mailbox: Mailbox) -> dict:
    """Pull new messages, thread-correlate by reference number in the subject (FR-057),
    or create a new Request (same spine as the web channel — FR-002/FR-014). Malformed
    messages are logged as a ParseFailure instead of raising or being silently dropped."""
    if mailbox.provider != MailboxProvider.MAILHOG:
        raise NotImplementedError(f"provider '{mailbox.provider.value}' isn't wired up in this build — only 'mailhog' is (local dev stand-in)")

    created, threaded, failed = 0, 0, 0
    for msg in fetch_messages():
        if mailbox.email_address.lower() not in [addr.lower() for addr in msg.to_addresses]:
            continue  # addressed to a different mailbox — leave it for that sync

        try:
            outcome = _process_message(db, mailbox, msg)
            created += outcome == "created"
            threaded += outcome == "threaded"
        except ValueError as exc:
            db.add(
                ParseFailure(
                    mailbox_id=mailbox.id,
                    raw_subject=msg.subject or None,
                    raw_from=msg.from_email or None,
                    error_message=str(exc),
                    raw_source=json.dumps(msg.raw),
                )
            )
            failed += 1
        delete_message(msg.external_id)

    mailbox.last_synced_at = utcnow()
    mailbox.status = MailboxStatus.CONNECTED
    db.commit()
    return {"created": created, "threaded": threaded, "failed": failed}


def _process_message(db: Session, mailbox: Mailbox, msg: InboundMessage) -> str:
    if not msg.from_email or "@" not in msg.from_email:
        raise ValueError("Missing or invalid From address")
    if not msg.body.strip() and not msg.subject.strip():
        raise ValueError("Empty message: no subject or body")

    ref_match = REFERENCE_RE.search(msg.subject)
    if ref_match:
        existing = db.execute(select(Request).where(Request.reference == ref_match.group().upper())).scalar_one_or_none()
        if existing:
            db.add(Message(request_id=existing.id, author=MessageAuthor.CUSTOMER, body=msg.body or msg.subject))
            record_audit_event(db, event_type="email.threaded", actor="email_engine", object_ref=f"request:{existing.id}", payload={"mailbox": mailbox.name})
            return "threaded"

    customer = db.execute(select(Customer).where(Customer.email == msg.from_email)).scalar_one_or_none()
    if customer is None:
        customer = Customer(email=msg.from_email, full_name=msg.from_email.split("@")[0])
        db.add(customer)
        db.flush()

    reference = f"REQ-{uuid.uuid4().hex[:8].upper()}"
    req = Request(reference=reference, customer_id=customer.id, channel=Channel.EMAIL, status=RequestStatus.RECEIVED, department_id=mailbox.department_id)
    db.add(req)
    db.flush()
    db.add(Message(request_id=req.id, author=MessageAuthor.CUSTOMER, body=msg.body or msg.subject))
    record_audit_event(db, event_type="request.created", actor="email_engine", object_ref=f"request:{req.id}", payload={"reference": reference, "channel": "email"})
    return "created"
