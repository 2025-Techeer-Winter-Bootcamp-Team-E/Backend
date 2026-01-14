"""
Cart item entity.
"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from shared.domain import BaseEntity


@dataclass
class CartItem(BaseEntity):
    """Cart item entity."""
    cart_id: UUID
    product_id: UUID
    product_name: str
    unit_price: Decimal
    quantity: int = 1

    @property
    def subtotal(self) -> Decimal:
        """Calculate the item subtotal."""
        return self.unit_price * self.quantity
