import uuid

from pydantic import BaseModel, EmailStr

from app.models.user import RoleName


class DepartmentOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    name: str
    slug: str


class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: RoleName
    department_id: uuid.UUID | None
    is_active: bool

    model_config = {"from_attributes": True}


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: RoleName
    department_id: uuid.UUID | None = None
    password: str


class AdminUserUpdate(BaseModel):
    role: RoleName | None = None
    department_id: uuid.UUID | None = None
    is_active: bool | None = None
