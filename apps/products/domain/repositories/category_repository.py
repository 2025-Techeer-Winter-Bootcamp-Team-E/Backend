"""
Category repository interface.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities.category import Category


class CategoryRepository(ABC):
    """Abstract repository for Category."""

    @abstractmethod
    def save(self, category: Category) -> Category:
        """Save a category."""
        pass

    @abstractmethod
    def find_by_id(self, category_id: UUID) -> Optional[Category]:
        """Find a category by ID."""
        pass

    @abstractmethod
    def find_all(self, parent_id: Optional[UUID] = None, is_active: bool = True) -> List[Category]:
        """Find all categories."""
        pass

    @abstractmethod
    def delete(self, category_id: UUID) -> bool:
        """Delete a category."""
        pass
