"""
Django ORM implementation of ProductRepository.
"""
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from django.db import transaction
from django.db.models import Q

from ...domain.entities.product import Product
from ...domain.repositories.product_repository import ProductRepository
from ...domain.value_objects.money import Money
from ...domain.value_objects.sku import SKU
from ...domain.value_objects.stock import Stock
from ...domain.value_objects.product_embedding import ProductEmbedding
from ..models.product_model import ProductModel


class DjangoProductRepository(ProductRepository):
    """Django ORM based product repository implementation."""

    def save(self, product: Product) -> Product:
        """Save a product entity."""
        with transaction.atomic():
            model, created = ProductModel.objects.update_or_create(
                id=product.id,
                defaults={
                    'name': product.name,
                    'description': product.description,
                    'sku': product.sku.value,
                    'price': product.price.amount,
                    'currency': product.price.currency,
                    'stock_quantity': product.stock.quantity,
                    'category_id': product.category_id,
                    'is_active': product.is_active,
                    'embedding': product.embedding.vector if product.embedding else None,
                    'images': product.images,
                }
            )
            return self._to_entity(model)

    def find_by_id(self, product_id: UUID) -> Optional[Product]:
        """Find a product by ID."""
        try:
            model = ProductModel.objects.get(id=product_id)
            return self._to_entity(model)
        except ProductModel.DoesNotExist:
            return None

    def find_by_sku(self, sku: str) -> Optional[Product]:
        """Find a product by SKU."""
        try:
            model = ProductModel.objects.get(sku=sku.upper())
            return self._to_entity(model)
        except ProductModel.DoesNotExist:
            return None

    def find_all(
        self,
        category_id: Optional[UUID] = None,
        is_active: bool = True,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Product]:
        """Find all products with optional filters."""
        queryset = ProductModel.objects.filter(is_active=is_active)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        models = queryset.order_by('-created_at')[offset:offset + limit]
        return [self._to_entity(model) for model in models]

    def find_by_embedding_similarity(
        self,
        embedding: ProductEmbedding,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> List[Product]:
        """Find products by embedding similarity using pgvector."""
        from pgvector.django import CosineDistance

        models = (
            ProductModel.objects
            .filter(is_active=True)
            .exclude(embedding__isnull=True)
            .annotate(distance=CosineDistance('embedding', embedding.vector))
            .filter(distance__lt=(1 - threshold))
            .order_by('distance')[:limit]
        )
        return [self._to_entity(model) for model in models]

    def search(
        self,
        query: str,
        category_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Product]:
        """Search products by text query."""
        queryset = ProductModel.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True,
        )
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        models = queryset.order_by('-created_at')[offset:offset + limit]
        return [self._to_entity(model) for model in models]

    def delete(self, product_id: UUID) -> bool:
        """Delete a product."""
        deleted, _ = ProductModel.objects.filter(id=product_id).delete()
        return deleted > 0

    def count(self, category_id: Optional[UUID] = None, is_active: bool = True) -> int:
        """Count products."""
        queryset = ProductModel.objects.filter(is_active=is_active)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset.count()

    def _to_entity(self, model: ProductModel) -> Product:
        """Convert Django model to domain entity."""
        return Product(
            id=model.id,
            name=model.name,
            description=model.description,
            sku=SKU(value=model.sku),
            price=Money(amount=Decimal(str(model.price)), currency=model.currency),
            stock=Stock(quantity=model.stock_quantity),
            category_id=model.category_id,
            is_active=model.is_active,
            embedding=ProductEmbedding(vector=model.embedding) if model.embedding else None,
            images=model.images or [],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
