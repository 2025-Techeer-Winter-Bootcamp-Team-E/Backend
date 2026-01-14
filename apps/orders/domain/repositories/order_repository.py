"""
Order repository interface.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities.order import Order
from ..value_objects.order_status import OrderStatus


class OrderRepository(ABC):
    """Abstract repository for Order aggregate."""

    @abstractmethod
    def save(self, order: Order) -> Order:
        """Save an order."""
        pass

    @abstractmethod
    def find_by_id(self, order_id: UUID) -> Optional[Order]:
        """Find an order by ID."""
        pass

    @abstractmethod
    def find_by_order_number(self, order_number: str) -> Optional[Order]:
        """Find an order by order number."""
        pass

    @abstractmethod
    def find_by_user_id(
        self,
        user_id: UUID,
        status: Optional[OrderStatus] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Order]:
        """Find orders by user ID."""
        pass

    @abstractmethod
    def delete(self, order_id: UUID) -> bool:
        """Delete an order."""
        pass
