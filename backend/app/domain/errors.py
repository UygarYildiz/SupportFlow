"""Domain errors. The API layer maps them to HTTP status codes.

Messages are shown to staff, so they are in Turkish (see the root CLAUDE.md).
"""

# Resource and entity names as staff read them in error messages.
_NAMES = {
    "Ticket": "Talep",
    "Run": "Analiz çalıştırması",
    "Order": "Sipariş",
    "Customer": "Müşteri",
    "Proposal": "Öneri",
    "User": "Kullanıcı",
    "ticket": "Talep",
    "proposal": "Öneri",
    "run": "Analiz çalıştırması",
}


class DomainError(Exception):
    """Base class for expected business-rule failures."""


class NotFoundError(DomainError):
    def __init__(self, resource: str, identifier: object) -> None:
        super().__init__(f"{_NAMES.get(resource, resource)} bulunamadı: {identifier}")
        self.resource = resource
        self.identifier = identifier


class ConflictError(DomainError):
    """The request conflicts with the current state of a resource."""


class InvalidStateTransitionError(ConflictError):
    def __init__(self, entity: str, current: str, target: str) -> None:
        super().__init__(
            f"{_NAMES.get(entity, entity)} '{current}' durumundan '{target}' durumuna geçemez"
        )
        self.entity = entity
        self.current = current
        self.target = target


class BusinessRuleViolationError(DomainError):
    """The request is well-formed but conflicts with a business rule."""


class ForbiddenError(DomainError):
    """The actor is authenticated but not allowed to do this."""
