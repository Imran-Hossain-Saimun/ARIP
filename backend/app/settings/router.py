from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.db import get_db
from app.core.permissions import Action, require_permission
from app.core.security import CurrentUser
from app.models.settings import AppSetting
from app.schemas.settings import AppSettingOut, AppSettingUpsert

router = APIRouter(prefix="/v1/settings", tags=["settings"])

# Seeded/default keys so the Settings screen always has something to show even before an
# admin has touched anything — §10: AI providers, retrieval config knobs.
DEFAULTS: dict[str, dict] = {
    "ai_providers": {"primary": "anthropic", "fallback": "openai"},
    "retrieval": {
        "chunk_size": 800,
        "overlap": 120,
        "vector_top_k": 8,
        "vectorless_depth": 3,
        "fusion": "reciprocal_rank",
        "min_score": 0.62,
        "rerank": True,
    },
}


@router.get("", response_model=list[AppSettingOut])
def list_settings(db: Annotated[Session, Depends(get_db)], _user=require_permission("integrations", Action.READ)) -> list[AppSetting]:
    existing = {row.key: row for row in db.execute(select(AppSetting)).scalars()}
    for key, value in DEFAULTS.items():
        if key not in existing:
            row = AppSetting(key=key, value=value)
            db.add(row)
            existing[key] = row
    db.commit()
    return list(existing.values())


@router.put("/{key}", response_model=AppSettingOut)
def upsert_setting(
    key: str,
    body: AppSettingUpsert,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, require_permission("integrations", Action.WRITE)],
) -> AppSetting:
    row = db.get(AppSetting, key)
    if row is None:
        row = AppSetting(key=key, value=body.value)
        db.add(row)
    else:
        row.value = body.value
    record_audit_event(db, event_type="settings.updated", actor=current_user.email, object_ref=f"setting:{key}", payload={"key": key, "value": body.value})
    db.commit()
    db.refresh(row)
    return row
