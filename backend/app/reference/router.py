from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import CurrentUser
from app.models.department import Department
from app.schemas.admin import DepartmentOut

router = APIRouter(prefix="/v1/departments", tags=["reference"])


@router.get("", response_model=list[DepartmentOut])
def list_departments_for_pickers(db: Annotated[Session, Depends(get_db)], _user: CurrentUser) -> list[Department]:
    """Low-sensitivity reference data (dept names/slugs) any authenticated user can read
    to populate pickers/filters — distinct from `/v1/admin/departments`, which is the
    admin-management surface gated by §12's `admin_users` module."""
    return list(db.execute(select(Department).order_by(Department.name)).scalars())
