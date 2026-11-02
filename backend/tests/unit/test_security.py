from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import DEV_JWT_SECRET, Settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.domain.enums import UserRole

SETTINGS = Settings(jwt_secret_key="unit-test-secret-0123456789abcdef0123")  # type: ignore[arg-type]


def test_password_hash_verifies_only_the_original_password() -> None:
    hashed = hash_password("s3cret-pass")
    assert hashed != "s3cret-pass"
    assert verify_password("s3cret-pass", hashed)
    assert not verify_password("wrong-pass", hashed)
    assert not verify_password("s3cret-pass", None)  # unknown user


def test_token_round_trip_keeps_user_and_role() -> None:
    token = create_access_token(42, UserRole.ADMIN, SETTINGS)
    claims = decode_access_token(token, SETTINGS)
    assert (claims.user_id, claims.role) == (42, UserRole.ADMIN)


def test_expired_token_is_rejected() -> None:
    issued = datetime.now(UTC) - timedelta(minutes=SETTINGS.access_token_expire_minutes + 1)
    token = create_access_token(1, UserRole.AGENT_USER, SETTINGS, now=issued)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SETTINGS)


def test_token_signed_with_another_secret_is_rejected() -> None:
    other = Settings(jwt_secret_key="another-secret-0123456789abcdef01234")  # type: ignore[arg-type]
    token = create_access_token(1, UserRole.ADMIN, other)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SETTINGS)


def test_production_refuses_the_development_secret() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(app_env="production", jwt_secret_key=DEV_JWT_SECRET)  # type: ignore[arg-type]
