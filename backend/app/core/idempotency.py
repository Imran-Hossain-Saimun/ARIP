from fastapi import Header, HTTPException, status

# In-process de-dup cache keyed by (endpoint, Idempotency-Key). Good enough for a single
# API process in dev; swap for a Redis-backed store (shared across replicas, with a TTL)
# before running more than one API instance.
_seen_keys: set[tuple[str, str]] = set()


def require_idempotency_key(idempotency_key: str = Header(..., alias="Idempotency-Key")) -> str:
    if not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "validation_failed", "message": "Idempotency-Key header is required.", "field_errors": [], "trace_id": None},
        )
    return idempotency_key


def check_and_record(endpoint: str, idempotency_key: str) -> bool:
    """Returns True the first time this (endpoint, key) pair is seen, False on replay."""
    seen_before = (endpoint, idempotency_key) in _seen_keys
    _seen_keys.add((endpoint, idempotency_key))
    return not seen_before
