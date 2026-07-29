import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.automation import ConfigResource, ConfigResourceKind, ConfigResourceStatus
from app.models.decision import Decision
from app.models.request import Request
from app.models.user import User


def get_resource_or_404(db: Session, resource_id: uuid.UUID) -> ConfigResource:
    resource = db.get(ConfigResource, resource_id)
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Config resource not found.", "field_errors": [], "trace_id": None},
        )
    return resource


def list_current(db: Session, kind: ConfigResourceKind) -> list[ConfigResource]:
    """One row per `key` — the active version if one exists, else the newest draft."""
    rows = list(db.execute(select(ConfigResource).where(ConfigResource.kind == kind).order_by(ConfigResource.version.desc())).scalars())
    by_key: dict[str, ConfigResource] = {}
    for row in rows:
        current = by_key.get(row.key)
        if current is None:
            by_key[row.key] = row
        elif row.status == ConfigResourceStatus.ACTIVE and current.status != ConfigResourceStatus.ACTIVE:
            by_key[row.key] = row
    return sorted(by_key.values(), key=lambda r: r.name)


def list_versions(db: Session, kind: ConfigResourceKind, key: str) -> list[ConfigResource]:
    stmt = select(ConfigResource).where(ConfigResource.kind == kind, ConfigResource.key == key).order_by(ConfigResource.version.desc())
    return list(db.execute(stmt).scalars())


def create_draft(db: Session, *, kind: ConfigResourceKind, key: str, name: str, config: dict, description: str | None, user: User) -> ConfigResource:
    max_version = db.execute(select(func.max(ConfigResource.version)).where(ConfigResource.kind == kind, ConfigResource.key == key)).scalar() or 0
    resource = ConfigResource(kind=kind, key=key, name=name, version=max_version + 1, status=ConfigResourceStatus.DRAFT, config=config, description=description, created_by=user.id)
    db.add(resource)
    db.flush()
    return resource


def publish(db: Session, resource: ConfigResource) -> ConfigResource:
    """Activate this version; archive whatever was previously active under the same
    (kind, key) — never more than one ACTIVE row per key."""
    previously_active = db.execute(
        select(ConfigResource).where(
            ConfigResource.kind == resource.kind,
            ConfigResource.key == resource.key,
            ConfigResource.status == ConfigResourceStatus.ACTIVE,
        )
    ).scalars()
    for row in previously_active:
        row.status = ConfigResourceStatus.ARCHIVED

    resource.status = ConfigResourceStatus.ACTIVE
    resource.activated_at = datetime.now(timezone.utc)
    db.flush()
    return resource


def rollback(db: Session, *, kind: ConfigResourceKind, key: str, target_version: int) -> ConfigResource:
    target = db.execute(
        select(ConfigResource).where(ConfigResource.kind == kind, ConfigResource.key == key, ConfigResource.version == target_version)
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": f"Version {target_version} of '{key}' not found.", "field_errors": [], "trace_id": None},
        )
    return publish(db, target)


# Fields a business-rule "when" clause is allowed to match against — kept to a small,
# explicit allowlist rather than arbitrary attribute access.
_MATCHABLE_FIELDS = {"category", "intent", "channel", "priority"}


def simulate_business_rule(db: Session, when: dict, days: int = 30) -> dict:
    """Dry-run a candidate rule's WHEN clause against the last `days` of real
    Decision+Request data — no rows are written. Supports equality matches on
    category/intent/channel/priority plus an optional `confidence_gte` threshold."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(Decision, Request).join(Request, Decision.request_id == Request.id).where(Decision.created_at >= since)

    for field, value in when.items():
        if field == "confidence_gte":
            stmt = stmt.where(Decision.confidence >= value)
        elif field in _MATCHABLE_FIELDS:
            stmt = stmt.where(getattr(Request, field) == value)

    rows = db.execute(stmt).all()
    matched = len(rows)
    would_change_outcome = sum(1 for decision, _ in rows if not decision.rule_overridden)
    return {"window_days": days, "matched": matched, "would_change_outcome": would_change_outcome}
