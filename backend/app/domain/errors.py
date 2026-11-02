"""Domain errors. The API layer maps them to HTTP status codes."""


class DomainError(Exception):
    """Base class for expected business-rule failures."""


class NotFoundError(DomainError):
    def __init__(self, resource: str, identifier: object) -> None:
        super().__init__(f"{resource} {identifier} not found")
        self.resource = resource
        self.identifier = identifier


class ConflictError(DomainError):
    """The request conflicts with the current state of a resource."""


class InvalidStateTransitionError(ConflictError):
    def __init__(self, entity: str, current: str, target: str) -> None:
        super().__init__(f"{entity} cannot move from '{current}' to '{target}'")
        self.entity = entity
        self.current = current
        self.target = target


class BusinessRuleViolationError(DomainError):
    """The request is well-formed but conflicts with a business rule."""
