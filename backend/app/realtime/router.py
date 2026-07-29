import json
import time
from typing import Annotated

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import CurrentUser
from app.models.audit import AuditEvent

router = APIRouter(prefix="/v1", tags=["realtime"])

# Dev-scale simplification: polls for new audit events every 2s rather than a real
# pub/sub push, and closes after ~2 minutes so the connection doesn't hang forever —
# the browser's EventSource reconnects automatically when a stream closes, which is
# the "SSE reconnect" behavior §13 asks for, just without server-side exponential backoff.
_POLL_INTERVAL_SECONDS = 2
_MAX_ITERATIONS = 60


def _event_stream():
    db = SessionLocal()
    try:
        yield "event: connected\ndata: {}\n\n"
        # Establish the watermark at the most recent existing event (if any) so we only
        # ever stream events that occur AFTER this connection opened, not a history dump.
        latest = db.execute(select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(1)).scalar_one_or_none()
        last_occurred_at = latest.occurred_at if latest else None

        for _ in range(_MAX_ITERATIONS):
            stmt = select(AuditEvent).order_by(AuditEvent.occurred_at)
            if last_occurred_at is not None:
                stmt = stmt.where(AuditEvent.occurred_at > last_occurred_at)
            new_events = list(db.execute(stmt).scalars())
            for event in new_events:
                payload = {"event_type": event.event_type, "actor": event.actor, "object_ref": event.object_ref, "occurred_at": event.occurred_at.isoformat()}
                yield f"event: audit_event\ndata: {json.dumps(payload)}\n\n"
                last_occurred_at = event.occurred_at
            yield ": heartbeat\n\n"
            time.sleep(_POLL_INTERVAL_SECONDS)
    finally:
        db.close()


@router.get("/stream")
def stream(_user: CurrentUser) -> StreamingResponse:
    return StreamingResponse(_event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})
