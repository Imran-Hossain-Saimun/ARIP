import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.db import get_db
from app.core.permissions import Action, require_permission
from app.core.security import CurrentUser, hash_password
from app.models.department import Department
from app.models.user import User
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserOut,
    AdminUserUpdate,
    DepartmentCreate,
    DepartmentOut,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("admin_users", Action.READ),
) -> list[Department]:
    return list(db.execute(select(Department).order_by(Department.name)).scalars())


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    body: DepartmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, require_permission("admin_users", Action.WRITE)],
) -> Department:
    dept = Department(name=body.name, slug=body.slug)
    db.add(dept)
    db.flush()
    record_audit_event(db, event_type="department.created", actor=current_user.email, object_ref=f"department:{dept.id}", payload={"name": body.name})
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _user=require_permission("admin_users", Action.READ),
) -> list[User]:
    return list(db.execute(select(User).order_by(User.full_name)).scalars())


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: AdminUserCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, require_permission("admin_users", Action.WRITE)],
) -> User:
    existing = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "validation_failed", "message": "A user with this email already exists.", "field_errors": [{"loc": ["email"], "msg": "already exists"}], "trace_id": None},
        )
    user = User(email=body.email, full_name=body.full_name, role=body.role, department_id=body.department_id, hashed_password=hash_password(body.password))
    db.add(user)
    db.flush()
    record_audit_event(db, event_type="user.created", actor=current_user.email, object_ref=f"user:{user.id}", payload={"email": body.email, "role": body.role.value})
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: uuid.UUID,
    body: AdminUserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, require_permission("admin_users", Action.WRITE)],
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "User not found.", "field_errors": [], "trace_id": None})

    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(user, field, value)

    record_audit_event(db, event_type="user.updated", actor=current_user.email, object_ref=f"user:{user.id}", payload=body.model_dump(exclude_unset=True, mode="json"))
    db.commit()
    db.refresh(user)
    return user
