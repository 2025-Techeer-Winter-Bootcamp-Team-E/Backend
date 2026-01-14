"""
Stock updated domain event.
"""
from dataclasses import dataclass
from uuid import UUID

from shared.domain import DomainEvent


@dataclass(frozen=True)
class StockUpdated(DomainEvent):
    """Event raised when product stock is updated."""
    product_id: UUID
    new_quantity: int
