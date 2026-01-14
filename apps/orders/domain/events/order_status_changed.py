"""
Order status changed domain event.
"""
from dataclasses import dataclass
from uuid import UUID

from shared.domain import DomainEvent


@dataclass(frozen=True)
class OrderStatusChanged(DomainEvent):
    """Event raised when order status changes."""
    order_id: UUID
    old_status: str
    new_status: str
