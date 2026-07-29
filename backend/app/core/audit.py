import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.base import utcnow


def _compute_hash(prev_hash: str | None, event_type: str, actor: str, object_ref: str, payload: dict) -> str:
    digest_input = json.dumps(
        {"prev_hash": prev_hash, "event_type": event_type, "actor": actor, "object_ref": object_ref, "payload": payload},
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(digest_input).hexdigest()}"


def record_audit_event(db: Session, *, event_type: str, actor: str, object_ref: str, payload: dict | None = None) -> AuditEvent:
    """The only sanctioned way to write an audit row (§13 non-negotiable: every mutation
    writes an audit event in the same transaction). Locks the last row so concurrent
    writers can't compute the same prev_hash and fork the chain."""
    payload = payload or {}
    last = db.execute(select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(1).with_for_update()).scalar_one_or_none()
    prev_hash = last.hash if last else None

    event = AuditEvent(
        event_type=event_type,
        actor=actor,
        object_ref=object_ref,
        payload=payload,
        prev_hash=prev_hash,
        hash=_compute_hash(prev_hash, event_type, actor, object_ref, payload),
        occurred_at=utcnow(),
    )
    db.add(event)
    db.flush()
    return event


def verify_chain(db: Session) -> tuple[bool, int, uuid.UUID | None]:
    """Walks every event in insertion order and recomputes each hash — returns
    (valid, event_count, id_of_first_broken_link_or_None). Used by the audit export/
    verify endpoint (§13 E2E target: "exported audit log hash-chain verifies")."""
    events = list(db.execute(select(AuditEvent).order_by(AuditEvent.occurred_at)).scalars())
    prev_hash: str | None = None
    for event in events:
        expected = _compute_hash(prev_hash, event.event_type, event.actor, event.object_ref, event.payload)
        if event.prev_hash != prev_hash or event.hash != expected:
            return False, len(events), event.id
        prev_hash = event.hash
    return True, len(events), None
