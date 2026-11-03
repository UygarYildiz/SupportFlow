"""Staff account rules and self-hosted configuration (ADR-017). Pure: no database."""

import sys

import pytest

from app.core.config import Settings
from app.domain.accounts import (
    MIN_PASSWORD_LENGTH,
    ensure_an_admin_remains,
    normalize_email,
    validate_new_password,
)
from app.domain.errors import BusinessRuleViolationError

STRONG_SECRET = "x" * 40


@pytest.mark.parametrize(
    ("password", "reason"),
    [
        ("short-pass", "en az"),
        ("p" * 129, "en fazla"),
        (" leading-space-password", "boşluk"),
        ("trailing-space-password ", "boşluk"),
        ("ayse@isletme.example", "e-posta"),
        ("AYSE@ISLETME.EXAMPLE", "e-posta"),
    ],
)
def test_weak_passwords_are_refused(password: str, reason: str) -> None:
    with pytest.raises(BusinessRuleViolationError, match=reason):
        validate_new_password(password, email="ayse@isletme.example")


def test_a_long_passphrase_is_accepted() -> None:
    validate_new_password("a" * MIN_PASSWORD_LENGTH, email="ayse@isletme.example")
    validate_new_password("kahve fincanı mavi kapı", email="ayse@isletme.example")


def test_emails_are_stored_in_one_canonical_form() -> None:
    assert normalize_email("  Ayse.Demir@Isletme.Example ") == "ayse.demir@isletme.example"
    for bad in ("ayse", "@isletme.example", "ayse@localhost", "ay se@isletme.example"):
        with pytest.raises(BusinessRuleViolationError):
            normalize_email(bad)


def test_an_installation_always_keeps_an_admin() -> None:
    ensure_an_admin_remains(1)
    with pytest.raises(BusinessRuleViolationError, match="yönetici"):
        ensure_an_admin_remains(0)


def test_self_hosted_production_requires_a_setup_token() -> None:
    base = {"app_env": "production", "jwt_secret_key": STRONG_SECRET}
    with pytest.raises(ValueError, match="SETUP_TOKEN"):
        Settings(deployment_mode="self_hosted", **base)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="SETUP_TOKEN"):
        Settings(deployment_mode="self_hosted", setup_token="too-short", **base)  # type: ignore[arg-type]
    Settings(deployment_mode="self_hosted", setup_token="s" * 16, **base)  # type: ignore[arg-type]
    # The demo (and development) does not need one.
    Settings(deployment_mode="demo", **base)  # type: ignore[arg-type]


def test_demo_data_is_never_seeded_into_a_self_hosted_installation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import seed_demo

    monkeypatch.setattr(seed_demo, "get_settings", lambda: Settings(deployment_mode="self_hosted"))
    monkeypatch.setattr(sys, "argv", ["seed_demo", "--reset"])
    with pytest.raises(SystemExit, match="self_hosted"):
        seed_demo.main()
