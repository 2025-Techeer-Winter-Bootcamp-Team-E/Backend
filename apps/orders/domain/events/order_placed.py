"""
Order placed domain event.
"""
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from shared.domain import DomainEvent


@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    """Event raised when a new order is placed."""
    order_id: UUID
    order_number: str
    user_id: UUID
    total_amount: Decimal
