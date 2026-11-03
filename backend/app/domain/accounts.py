"""Staff account rules (ADR-017): pure functions, no database.

Self-hosted installations manage their own staff, so these rules protect an
installation from weak passwords and from locking itself out.
"""

from app.domain.errors import BusinessRuleViolationError

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128  # Argon2 accepts more; the cap keeps hashing cost bounded


def validate_new_password(password: str, *, email: str) -> None:
    """Raise if `password` is not acceptable for a new or changed account password."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise BusinessRuleViolationError(f"Parola en az {MIN_PASSWORD_LENGTH} karakter olmalı")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise BusinessRuleViolationError(f"Parola en fazla {MAX_PASSWORD_LENGTH} karakter olabilir")
    if password.strip() != password or not password.strip():
        raise BusinessRuleViolationError("Parola boşlukla başlayamaz ya da bitemez")
    if password.casefold() == email.casefold() or password.casefold() in email.casefold():
        raise BusinessRuleViolationError("Parola e-posta adresini içeremez")


def normalize_email(email: str) -> str:
    """Accounts are matched case-insensitively; store one canonical form."""
    normalized = email.strip().lower()
    local, sep, domain = normalized.partition("@")
    if not sep or not local or "." not in domain or " " in normalized:
        raise BusinessRuleViolationError("Geçerli bir e-posta adresi girin")
    return normalized


def ensure_an_admin_remains(active_admins_after_change: int) -> None:
    """An installation must always keep at least one active admin, or nobody can manage it."""
    if active_admins_after_change < 1:
        raise BusinessRuleViolationError("En az bir etkin yönetici kalmalı")
