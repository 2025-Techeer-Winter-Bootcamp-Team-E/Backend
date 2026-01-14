"""
Domain exceptions.
"""


class DomainException(Exception):
    """Base exception for domain layer."""

    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(self.message)


class EntityNotFoundError(DomainException):
    """Raised when an entity is not found."""

    def __init__(self, entity_name: str, entity_id: str):
        super().__init__(
            message=f"{entity_name} with id '{entity_id}' not found",
            code="ENTITY_NOT_FOUND"
        )
        self.entity_name = entity_name
        self.entity_id = entity_id


class ValidationError(DomainException):
    """Raised when validation fails."""

    def __init__(self, message: str, field: str = None):
        super().__init__(message=message, code="VALIDATION_ERROR")
        self.field = field


class BusinessRuleViolationError(DomainException):
    """Raised when a business rule is violated."""

    def __init__(self, message: str, rule: str = None):
        super().__init__(message=message, code="BUSINESS_RULE_VIOLATION")
        self.rule = rule


class InsufficientStockError(DomainException):
    """Raised when stock is insufficient."""

    def __init__(self, product_id: str, requested: int, available: int):
        super().__init__(
            message=f"Insufficient stock for product '{product_id}': requested {requested}, available {available}",
            code="INSUFFICIENT_STOCK"
        )
        self.product_id = product_id
        self.requested = requested
        self.available = available


class InvalidOperationError(DomainException):
    """Raised when an operation is invalid for the current state."""

    def __init__(self, message: str, operation: str = None, state: str = None):
        super().__init__(message=message, code="INVALID_OPERATION")
        self.operation = operation
        self.state = state
