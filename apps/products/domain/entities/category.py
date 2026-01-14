"""
Category entity.
"""
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from shared.domain import AggregateRoot


@dataclass
class Category(AggregateRoot):
    """Category entity for organizing products."""
    name: str
    description: str = ""
    parent_id: Optional[UUID] = None
    is_active: bool = True

    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        parent_id: Optional[UUID] = None,
    ) -> 'Category':
        """Factory method to create a new category."""
        return cls(
            name=name,
            description=description,
            parent_id=parent_id,
        )

    def update(self, name: Optional[str] = None, description: Optional[str] = None) -> None:
        """Update category information."""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        self.touch()

    def deactivate(self) -> None:
        """Deactivate the category."""
        self.is_active = False
        self.touch()

    def activate(self) -> None:
        """Activate the category."""
        self.is_active = True
        self.touch()
