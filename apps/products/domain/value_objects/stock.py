"""
Stock value object.
"""
from dataclasses import dataclass

from shared.domain import ValueObject


@dataclass(frozen=True)
class Stock(ValueObject):
    """Stock quantity value object."""
    quantity: int

    def __post_init__(self):
        if self.quantity < 0:
            raise ValueError("Stock quantity cannot be negative")

    @property
    def is_available(self) -> bool:
        """Check if stock is available."""
        return self.quantity > 0

    @property
    def is_low(self) -> bool:
        """Check if stock is low (less than 10)."""
        return self.quantity < 10
