"""
Order domain exceptions.
"""
from shared.domain.exceptions import DomainException, InvalidOperationError


class OrderNotFoundError(DomainException):
    """Raised when an order is not found."""

    def __init__(self, identifier: str):
        super().__init__(
            message=f"Order '{identifier}' not found",
            code="ORDER_NOT_FOUND"
        )
        self.identifier = identifier


class CartNotFoundError(DomainException):
    """Raised when a cart is not found."""

    def __init__(self, identifier: str):
        super().__init__(
            message=f"Cart '{identifier}' not found",
            code="CART_NOT_FOUND"
        )
        self.identifier = identifier


class EmptyCartError(DomainException):
    """Raised when trying to checkout an empty cart."""

    def __init__(self):
        super().__init__(
            message="Cannot checkout an empty cart",
            code="EMPTY_CART"
        )


class InvalidOrderStateError(InvalidOperationError):
    """Raised when an order operation is invalid for the current state."""

    def __init__(self, operation: str, current_state: str):
        super().__init__(
            message=f"Cannot {operation} order in '{current_state}' state",
            operation=operation,
            state=current_state,
        )
