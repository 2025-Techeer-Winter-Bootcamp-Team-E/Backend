"""
Categories business logic services.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from django.db import transaction

from .models import CategoryModel
from .exceptions import (
    CategoryNotFoundError,
    CategoryAlreadyExistsError,
    InvalidCategoryHierarchyError,
)

logger = logging.getLogger(__name__)


class CategoryService:
    """Service for category operations."""

    def get_category_by_id(self, category_id: int) -> Optional[CategoryModel]:
        """Get category by ID."""
        try:
            return CategoryModel.objects.get(id=category_id, deleted_at__isnull=True)
        except CategoryModel.DoesNotExist:
            return None

    def get_all_categories(self) -> List[CategoryModel]:
        """Get all active categories."""
        return list(
            CategoryModel.objects.filter(deleted_at__isnull=True)
            .order_by('name')
        )

    def get_root_categories(self) -> List[CategoryModel]:
        """Get top-level categories (no parent)."""
        return list(
            CategoryModel.objects.filter(
                parent__isnull=True,
                deleted_at__isnull=True
            ).order_by('name')
        )

    def get_subcategories(self, parent_id: int) -> List[CategoryModel]:
        """Get direct children of a category."""
        return list(
            CategoryModel.objects.filter(
                parent_id=parent_id,
                deleted_at__isnull=True
            ).order_by('name')
        )

    def get_category_tree(self) -> List[Dict[str, Any]]:
        """Get full category tree structure."""
        root_categories = self.get_root_categories()
        return [self._build_tree_node(cat) for cat in root_categories]

    @transaction.atomic
    def create_category(
        self,
        name: str,
        parent_id: Optional[int] = None,
    ) -> CategoryModel:
        """Create a new category."""
        parent = None
        if parent_id:
            parent = self.get_category_by_id(parent_id)
            if not parent:
                raise CategoryNotFoundError(category_id=parent_id)

        existing = CategoryModel.objects.filter(
            name__iexact=name,
            parent=parent,
            deleted_at__isnull=True
        ).exists()
        if existing:
            raise CategoryAlreadyExistsError(name=name)

        category = CategoryModel.objects.create(
            name=name,
            parent=parent,
        )

        logger.info(f"Created category: {category.name} ({category.id})")
        return category

    @transaction.atomic
    def update_category(
        self,
        category_id: int,
        name: str = None,
        parent_id: int = None,
    ) -> CategoryModel:
        """Update a category."""
        category = self.get_category_by_id(category_id)
        if not category:
            raise CategoryNotFoundError(category_id=category_id)

        if name is not None:
            category.name = name

        if parent_id is not None:
            if parent_id == category_id:
                raise InvalidCategoryHierarchyError("Category cannot be its own parent")
            if parent_id == 0:
                category.parent = None
            else:
                new_parent = self.get_category_by_id(parent_id)
                if not new_parent:
                    raise CategoryNotFoundError(category_id=parent_id)
                category.parent = new_parent

        category.save()
        logger.info(f"Updated category: {category.name} ({category.id})")
        return category

    @transaction.atomic
    def delete_category(self, category_id: int) -> bool:
        """Soft delete a category."""
        category = self.get_category_by_id(category_id)
        if not category:
            raise CategoryNotFoundError(category_id=category_id)

        category.deleted_at = datetime.now()
        category.save()
        logger.info(f"Deleted category: {category_id}")
        return True

    def _build_tree_node(self, category: CategoryModel) -> Dict[str, Any]:
        """Build a tree node for category."""
        children = CategoryModel.objects.filter(
            parent=category,
            deleted_at__isnull=True
        ).order_by('name')

        return {
            'id': category.id,
            'name': category.name,
            'level': category.level,
            'children': [self._build_tree_node(child) for child in children]
        }
