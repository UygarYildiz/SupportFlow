from typing import Literal

from pydantic import BaseModel, Field

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
