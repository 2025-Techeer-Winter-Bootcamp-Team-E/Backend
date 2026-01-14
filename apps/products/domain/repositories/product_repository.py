"""
Product repository interface.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities.product import Product
from ..value_objects.product_embedding import ProductEmbedding


class ProductRepository(ABC):
    """Abstract repository for Product aggregate."""

    @abstractmethod
    def save(self, product: Product) -> Product:
        """Save a product."""
        pass

    @abstractmethod
    def find_by_id(self, product_id: UUID) -> Optional[Product]:
        """Find a product by ID."""
        pass

    @abstractmethod
    def find_by_sku(self, sku: str) -> Optional[Product]:
        """Find a product by SKU."""
        pass

    @abstractmethod
    def find_all(
        self,
        category_id: Optional[UUID] = None,
        is_active: bool = True,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Product]:
        """Find all products with optional filters."""
        pass

    @abstractmethod
    def find_by_embedding_similarity(
        self,
        embedding: ProductEmbedding,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> List[Product]:
        """Find products by embedding similarity using pgvector."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        category_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Product]:
        """Search products by text query."""
        pass

    @abstractmethod
    def delete(self, product_id: UUID) -> bool:
        """Delete a product."""
        pass

    @abstractmethod
    def count(self, category_id: Optional[UUID] = None, is_active: bool = True) -> int:
        """Count products."""
        pass
