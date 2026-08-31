from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.app.models import UserRole


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    role: UserRole
    is_active: bool


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


class LoginResponse(AccessTokenResponse):
    pass
