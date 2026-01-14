"""
Product DTOs.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from ...domain.entities.product import Product


@dataclass
class ProductCreateDTO:
    """DTO for creating a product."""
    name: str
    description: str
    sku: str
    price: Decimal
    currency: str
    stock_quantity: int
    category_id: UUID
    images: Optional[List[str]] = None


@dataclass
class ProductUpdateDTO:
    """DTO for updating a product."""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = None


@dataclass
class ProductDTO:
    """DTO for product output."""
    id: UUID
    name: str
    description: str
    sku: str
    price: Decimal
    currency: str
    stock_quantity: int
    category_id: UUID
    is_active: bool
    is_in_stock: bool
    images: List[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, product: Product) -> 'ProductDTO':
        """Create DTO from entity."""
        return cls(
            id=product.id,
            name=product.name,
            description=product.description,
            sku=product.sku.value,
            price=product.price.amount,
            currency=product.price.currency,
            stock_quantity=product.stock.quantity,
            category_id=product.category_id,
            is_active=product.is_active,
            is_in_stock=product.is_in_stock,
            images=product.images,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )
