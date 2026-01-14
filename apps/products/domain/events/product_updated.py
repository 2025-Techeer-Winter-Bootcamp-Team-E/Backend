"""
Product updated domain event.
"""
from dataclasses import dataclass
from uuid import UUID

from shared.domain import DomainEvent


@dataclass(frozen=True)
class ProductUpdated(DomainEvent):
    """Event raised when a product is updated."""
    product_id: UUID
    name: str
