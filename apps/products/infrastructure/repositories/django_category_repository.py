"""
Django ORM implementation of CategoryRepository.
"""
from typing import List, Optional
from uuid import UUID

from django.db import transaction

from ...domain.entities.category import Category
from ...domain.repositories.category_repository import CategoryRepository
from ..models.category_model import CategoryModel


class DjangoCategoryRepository(CategoryRepository):
    """Django ORM based category repository implementation."""

    def save(self, category: Category) -> Category:
        """Save a category entity."""
        with transaction.atomic():
            model, created = CategoryModel.objects.update_or_create(
                id=category.id,
                defaults={
                    'name': category.name,
                    'description': category.description,
                    'parent_id': category.parent_id,
                    'is_active': category.is_active,
                }
            )
            return self._to_entity(model)

    def find_by_id(self, category_id: UUID) -> Optional[Category]:
        """Find a category by ID."""
        try:
            model = CategoryModel.objects.get(id=category_id)
            return self._to_entity(model)
        except CategoryModel.DoesNotExist:
            return None

    def find_all(self, parent_id: Optional[UUID] = None, is_active: bool = True) -> List[Category]:
        """Find all categories."""
        queryset = CategoryModel.objects.filter(is_active=is_active)
        if parent_id is not None:
            queryset = queryset.filter(parent_id=parent_id)
        else:
            queryset = queryset.filter(parent__isnull=True)
        return [self._to_entity(model) for model in queryset]

    def delete(self, category_id: UUID) -> bool:
        """Delete a category."""
        deleted, _ = CategoryModel.objects.filter(id=category_id).delete()
        return deleted > 0

    def _to_entity(self, model: CategoryModel) -> Category:
        """Convert Django model to domain entity."""
        return Category(
            id=model.id,
            name=model.name,
            description=model.description,
            parent_id=model.parent_id,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
