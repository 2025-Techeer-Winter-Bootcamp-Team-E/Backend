"""
Money value object.
"""
from dataclasses import dataclass
from decimal import Decimal

from shared.domain import ValueObject


@dataclass(frozen=True)
class Money(ValueObject):
    """Money value object with currency."""
    amount: Decimal
    currency: str = "KRW"

    def __post_init__(self):
        # Convert to Decimal if needed
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))

    def add(self, other: 'Money') -> 'Money':
        """Add two money values."""
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def subtract(self, other: 'Money') -> 'Money':
        """Subtract money value."""
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def multiply(self, factor: int) -> 'Money':
        """Multiply money by a factor."""
        return Money(amount=self.amount * factor, currency=self.currency)

    @property
    def formatted(self) -> str:
        """Get formatted money string."""
        if self.currency == "KRW":
            return f"{int(self.amount):,}원"
        return f"{self.currency} {self.amount:,.2f}"
