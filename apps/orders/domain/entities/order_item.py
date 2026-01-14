"""
Order item entity.
"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from shared.domain import BaseEntity


@dataclass
class OrderItem(BaseEntity):
    """Order item entity."""
    order_id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    quantity: int
    unit_price: Decimal
    currency: str = "KRW"

    @property
    def subtotal(self) -> Decimal:
        """Calculate the item subtotal."""
        return self.unit_price * self.quantity
