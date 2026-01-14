"""
Order entity (Aggregate Root).
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from shared.domain import AggregateRoot
from ..value_objects.order_status import OrderStatus
from ..value_objects.shipping_info import ShippingInfo
from ..value_objects.order_number import OrderNumber
from ..events.order_placed import OrderPlaced
from ..events.order_status_changed import OrderStatusChanged
from ..exceptions import InvalidOrderStateError
from .order_item import OrderItem


@dataclass
class Order(AggregateRoot):
    """Order entity representing a customer order."""
    order_number: OrderNumber
    user_id: UUID
    items: List[OrderItem]
    status: OrderStatus = OrderStatus.PENDING
    shipping_info: Optional[ShippingInfo] = None
    total_amount: Decimal = Decimal('0')
    notes: str = ""

    def __post_init__(self):
        self._calculate_total()

    def _calculate_total(self) -> None:
        """Calculate the total order amount."""
        self.total_amount = sum(item.subtotal for item in self.items)

    @classmethod
    def create(
        cls,
        user_id: UUID,
        items: List[OrderItem],
        shipping_info: ShippingInfo,
        notes: str = "",
    ) -> 'Order':
        """Factory method to create a new order."""
        order = cls(
            order_number=OrderNumber.generate(),
            user_id=user_id,
            items=items,
            shipping_info=shipping_info,
            notes=notes,
        )
        order.add_domain_event(
            OrderPlaced(
                order_id=order.id,
                order_number=order.order_number.value,
                user_id=user_id,
                total_amount=order.total_amount,
            )
        )
        return order

    def confirm(self) -> None:
        """Confirm the order."""
        if self.status != OrderStatus.PENDING:
            raise InvalidOrderStateError("confirm", self.status.value)
        self._change_status(OrderStatus.CONFIRMED)

    def process(self) -> None:
        """Start processing the order."""
        if self.status != OrderStatus.CONFIRMED:
            raise InvalidOrderStateError("process", self.status.value)
        self._change_status(OrderStatus.PROCESSING)

    def ship(self) -> None:
        """Ship the order."""
        if self.status != OrderStatus.PROCESSING:
            raise InvalidOrderStateError("ship", self.status.value)
        self._change_status(OrderStatus.SHIPPED)

    def deliver(self) -> None:
        """Mark the order as delivered."""
        if self.status != OrderStatus.SHIPPED:
            raise InvalidOrderStateError("deliver", self.status.value)
        self._change_status(OrderStatus.DELIVERED)

    def cancel(self) -> None:
        """Cancel the order."""
        if self.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
            raise InvalidOrderStateError("cancel", self.status.value)
        self._change_status(OrderStatus.CANCELLED)

    def _change_status(self, new_status: OrderStatus) -> None:
        """Change order status and emit event."""
        old_status = self.status
        self.status = new_status
        self.touch()
        self.add_domain_event(
            OrderStatusChanged(
                order_id=self.id,
                old_status=old_status.value,
                new_status=new_status.value,
            )
        )

    @property
    def is_cancellable(self) -> bool:
        """Check if the order can be cancelled."""
        return self.status not in [OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]

    @property
    def item_count(self) -> int:
        """Get the total number of items."""
        return sum(item.quantity for item in self.items)
