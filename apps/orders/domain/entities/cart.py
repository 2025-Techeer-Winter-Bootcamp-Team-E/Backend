"""
Cart entity (Aggregate Root).
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from shared.domain import AggregateRoot
from .cart_item import CartItem


@dataclass
class Cart(AggregateRoot):
    """Shopping cart entity."""
    user_id: UUID
    items: List[CartItem] = field(default_factory=list)

    @classmethod
    def create(cls, user_id: UUID) -> 'Cart':
        """Create a new cart for a user."""
        return cls(user_id=user_id)

    def add_item(
        self,
        product_id: UUID,
        product_name: str,
        unit_price: Decimal,
        quantity: int = 1,
    ) -> None:
        """Add an item to the cart or update quantity if exists."""
        existing = self._find_item(product_id)
        if existing:
            existing.quantity += quantity
        else:
            self.items.append(
                CartItem(
                    cart_id=self.id,
                    product_id=product_id,
                    product_name=product_name,
                    unit_price=unit_price,
                    quantity=quantity,
                )
            )
        self.touch()

    def update_item_quantity(self, product_id: UUID, quantity: int) -> None:
        """Update the quantity of an item."""
        item = self._find_item(product_id)
        if item:
            if quantity <= 0:
                self.remove_item(product_id)
            else:
                item.quantity = quantity
            self.touch()

    def remove_item(self, product_id: UUID) -> None:
        """Remove an item from the cart."""
        self.items = [item for item in self.items if item.product_id != product_id]
        self.touch()

    def clear(self) -> None:
        """Clear all items from the cart."""
        self.items = []
        self.touch()

    def _find_item(self, product_id: UUID) -> Optional[CartItem]:
        """Find an item in the cart by product ID."""
        for item in self.items:
            if item.product_id == product_id:
                return item
        return None

    @property
    def total_amount(self) -> Decimal:
        """Calculate the total cart amount."""
        return sum(item.subtotal for item in self.items)

    @property
    def item_count(self) -> int:
        """Get the total number of items."""
        return sum(item.quantity for item in self.items)

    @property
    def is_empty(self) -> bool:
        """Check if the cart is empty."""
        return len(self.items) == 0
