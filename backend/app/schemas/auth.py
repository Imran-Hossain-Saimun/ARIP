import uuid

from pydantic import BaseModel, EmailStr

from app.models.user import RoleName


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: RoleName
    department_id: uuid.UUID | None

    model_config = {"from_attributes": True}
