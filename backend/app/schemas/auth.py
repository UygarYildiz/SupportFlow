from typing import Literal

from pydantic import BaseModel, Field

from app.domain.accounts import MAX_PASSWORD_LENGTH
from app.domain.enums import UserRole
from app.schemas.common import ApiModel


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 (OAuth token type, not a secret)
    expires_in: int = Field(description="Lifetime in seconds")


class UserOut(ApiModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    full_name: str = Field(min_length=1, max_length=120)
    role: UserRole = UserRole.AGENT_USER
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class UserUpdate(BaseModel):
    """Only the fields that are sent change."""

    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(
        default=None, min_length=1, max_length=MAX_PASSWORD_LENGTH, description="Reset"
    )


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)
    new_password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)
