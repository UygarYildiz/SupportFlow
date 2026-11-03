from typing import Literal

from pydantic import BaseModel, Field

from app.domain.accounts import MAX_PASSWORD_LENGTH


class SetupStatusOut(BaseModel):
    mode: Literal["demo", "self_hosted"] = Field(
        description="`demo`: synthetic data and demo logins; `self_hosted`: one business's own data"
    )
    setup_required: bool = Field(description="True until the first admin has been created")
    setup_token_required: bool
    organization_name: str | None


class SetupRequest(BaseModel):
    organization_name: str = Field(min_length=1, max_length=120)
    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)
    setup_token: str | None = Field(default=None, max_length=256)
