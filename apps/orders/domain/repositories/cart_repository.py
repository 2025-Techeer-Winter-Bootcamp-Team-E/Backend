"""
Cart repository interface.
"""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from ..entities.cart import Cart


class CartRepository(ABC):
    """Abstract repository for Cart aggregate."""

    @abstractmethod
    def save(self, cart: Cart) -> Cart:
        """Save a cart."""
        pass

    @abstractmethod
    def find_by_id(self, cart_id: UUID) -> Optional[Cart]:
        """Find a cart by ID."""
        pass

    @abstractmethod
    def find_by_user_id(self, user_id: UUID) -> Optional[Cart]:
        """Find a cart by user ID."""
        pass

    @abstractmethod
    def delete(self, cart_id: UUID) -> bool:
        """Delete a cart."""
        pass
