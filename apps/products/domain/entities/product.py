"""
Product entity (Aggregate Root).
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from shared.domain import AggregateRoot
from ..value_objects.money import Money
from ..value_objects.sku import SKU
from ..value_objects.stock import Stock
from ..value_objects.product_embedding import ProductEmbedding
from ..events.product_created import ProductCreated
from ..events.product_updated import ProductUpdated
from ..events.stock_updated import StockUpdated
from ..exceptions import InsufficientStockError, InvalidProductError


@dataclass
class Product(AggregateRoot):
    """Product entity representing a sellable item."""
    name: str
    description: str
    sku: SKU
    price: Money
    stock: Stock
    category_id: UUID
    is_active: bool = True
    embedding: Optional[ProductEmbedding] = None
    images: List[str] = field(default_factory=list)

    def __post_init__(self):
        self._validate()

    def _validate(self) -> None:
        """Validate product data."""
        if not self.name or len(self.name) < 2:
            raise InvalidProductError("Product name must be at least 2 characters")
        if self.price.amount < 0:
            raise InvalidProductError("Price must be non-negative")

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        sku: str,
        price: Decimal,
        currency: str,
        stock_quantity: int,
        category_id: UUID,
        images: Optional[List[str]] = None,
    ) -> 'Product':
        """Factory method to create a new product."""
        product = cls(
            name=name,
            description=description,
            sku=SKU(value=sku),
            price=Money(amount=price, currency=currency),
            stock=Stock(quantity=stock_quantity),
            category_id=category_id,
            images=images or [],
        )
        product.add_domain_event(
            ProductCreated(
                product_id=product.id,
                name=product.name,
                sku=product.sku.value,
            )
        )
        return product

    def update_info(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[Money] = None,
    ) -> None:
        """Update product information."""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if price is not None:
            self.price = price
        self.touch()
        self.add_domain_event(
            ProductUpdated(product_id=self.id, name=self.name)
        )

    def decrease_stock(self, quantity: int) -> None:
        """Decrease stock by the given quantity."""
        if self.stock.quantity < quantity:
            raise InsufficientStockError(
                product_id=str(self.id),
                requested=quantity,
                available=self.stock.quantity,
            )
        self.stock = Stock(quantity=self.stock.quantity - quantity)
        self.touch()
        self.add_domain_event(
            StockUpdated(
                product_id=self.id,
                new_quantity=self.stock.quantity,
            )
        )

    def increase_stock(self, quantity: int) -> None:
        """Increase stock by the given quantity."""
        self.stock = Stock(quantity=self.stock.quantity + quantity)
        self.touch()
        self.add_domain_event(
            StockUpdated(
                product_id=self.id,
                new_quantity=self.stock.quantity,
            )
        )

    def set_embedding(self, embedding: ProductEmbedding) -> None:
        """Set the product embedding for semantic search."""
        self.embedding = embedding
        self.touch()

    def deactivate(self) -> None:
        """Deactivate the product."""
        self.is_active = False
        self.touch()

    def activate(self) -> None:
        """Activate the product."""
        self.is_active = True
        self.touch()

    def add_image(self, image_url: str) -> None:
        """Add an image to the product."""
        self.images.append(image_url)
        self.touch()

    def remove_image(self, image_url: str) -> None:
        """Remove an image from the product."""
        if image_url in self.images:
            self.images.remove(image_url)
            self.touch()

    @property
    def is_in_stock(self) -> bool:
        """Check if product is in stock."""
        return self.stock.quantity > 0
