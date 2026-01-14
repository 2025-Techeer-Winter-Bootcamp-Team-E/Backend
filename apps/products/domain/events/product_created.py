"""
Product created domain event.
"""
from dataclasses import dataclass
from uuid import UUID

from shared.domain import DomainEvent


@dataclass(frozen=True)
class ProductCreated(DomainEvent):
    """Event raised when a new product is created."""
    product_id: UUID
    name: str
    sku: str
