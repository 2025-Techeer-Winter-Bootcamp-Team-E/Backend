"""
Orders module service layer.
"""
from datetime import datetime
from typing import Optional, List

from django.db import transaction

from .models import (
    CartModel,
    CartItemModel,
    OrderModel,
    OrderItemModel,
    OrderHistoryModel,
    ReviewModel,
)
from .exceptions import (
    OrderNotFoundError,
    CartNotFoundError,
    EmptyCartError,
)


class CartService:
    """
    Cart (장바구니) business logic service.
    """

    def get_or_create_cart(self, user_id: int) -> CartModel:
        """Get or create cart for a user."""
        cart, created = CartModel.objects.get_or_create(
            user_id=user_id,
            deleted_at__isnull=True
        )
        return cart

    def get_cart_items(self, cart_id: int) -> List[CartItemModel]:
        """Get all items in a cart."""
        return list(
            CartItemModel.objects.filter(
                cart_id=cart_id,
                deleted_at__isnull=True
            ).select_related('product')
        )

    def add_item(
        self,
        cart_id: int,
        product_id: int,
        quantity: int = 1,
    ) -> CartItemModel:
        """Add item to cart."""
        cart_item, created = CartItemModel.objects.get_or_create(
            cart_id=cart_id,
            product_id=product_id,
            deleted_at__isnull=True,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return cart_item

    def update_item_quantity(
        self,
        cart_id: int,
        product_id: int,
        quantity: int,
    ) -> Optional[CartItemModel]:
        """Update cart item quantity."""
        try:
            cart_item = CartItemModel.objects.get(
                cart_id=cart_id,
                product_id=product_id,
                deleted_at__isnull=True
            )
            if quantity <= 0:
                cart_item.deleted_at = datetime.now()
                cart_item.save()
                return None
            else:
                cart_item.quantity = quantity
                cart_item.save()
                return cart_item
        except CartItemModel.DoesNotExist:
            raise CartNotFoundError(f"Cart {cart_id}")

    def remove_item(self, cart_id: int, product_id: int) -> bool:
        """Remove item from cart (soft delete)."""
        try:
            cart_item = CartItemModel.objects.get(
                cart_id=cart_id,
                product_id=product_id,
                deleted_at__isnull=True
            )
            cart_item.deleted_at = datetime.now()
            cart_item.save()
            return True
        except CartItemModel.DoesNotExist:
            return False

    def clear_cart(self, cart_id: int) -> bool:
        """Clear all items from cart (soft delete)."""
        CartItemModel.objects.filter(
            cart_id=cart_id,
            deleted_at__isnull=True
        ).update(deleted_at=datetime.now())
        return True


class OrderService:
    """
    Order business logic service.
    """

    def __init__(self):
        self.cart_service = CartService()

    def get_order_by_id(self, order_id: int) -> Optional[OrderModel]:
        """Get order by ID."""
        try:
            return OrderModel.objects.prefetch_related('items').get(
                id=order_id,
                deleted_at__isnull=True
            )
        except OrderModel.DoesNotExist:
            return None

    def get_user_orders(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> List[OrderModel]:
        """Get all orders for a user."""
        return list(
            OrderModel.objects.filter(user_id=user_id, deleted_at__isnull=True)
            .prefetch_related('items')
            .order_by('-created_at')[offset:offset + limit]
        )

    @transaction.atomic
    def create_order_from_cart(self, user_id: int) -> OrderModel:
        """Create order from user's cart items."""
        cart = self.cart_service.get_or_create_cart(user_id)
        cart_items = self.cart_service.get_cart_items(cart.id)
        if not cart_items:
            raise EmptyCartError()

        # Create order
        order = OrderModel.objects.create(user_id=user_id)

        # Create order items from cart items
        for cart_item in cart_items:
            # Use the product's danawa_product_id
            danawa_product_id = cart_item.product.danawa_product_id if cart_item.product else ''
            OrderItemModel.objects.create(
                order=order,
                danawa_product_id=danawa_product_id,
                quantity=cart_item.quantity,
            )

        # Clear the cart
        self.cart_service.clear_cart(cart.id)

        return order


class OrderHistoryService:
    """
    Order history business logic service.
    """

    def get_user_order_histories(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> List[OrderHistoryModel]:
        """Get order histories for a user."""
        return list(
            OrderHistoryModel.objects.filter(user_id=user_id, deleted_at__isnull=True)
            .order_by('-transaction_at')[offset:offset + limit]
        )

    def create_order_history(
        self,
        user_id: int,
        transaction_type: str,
        token_change: int,
        token_balance_after: int,
        danawa_product_id: str,
    ) -> OrderHistoryModel:
        """Create an order history record."""
        return OrderHistoryModel.objects.create(
            user_id=user_id,
            transaction_type=transaction_type,
            token_change=token_change,
            token_balance_after=token_balance_after,
            transaction_at=datetime.now(),
            danawa_product_id=danawa_product_id,
        )


class ReviewService:
    """
    Review business logic service.
    """

    def get_product_reviews(
        self,
        danawa_product_id: str,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ReviewModel]:
        """Get reviews for a product."""
        return list(
            ReviewModel.objects.filter(
                danawa_product_id=danawa_product_id,
                deleted_at__isnull=True
            ).order_by('-created_at')[offset:offset + limit]
        )

    def get_user_reviews(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ReviewModel]:
        """Get reviews by a user."""
        return list(
            ReviewModel.objects.filter(user_id=user_id, deleted_at__isnull=True)
            .order_by('-created_at')[offset:offset + limit]
        )

    def create_review(
        self,
        danawa_product_id: str,
        user_id: int,
        content: str = None,
        rating: int = None,
        mall_name: str = None,
        reviewer_name: str = None,
    ) -> ReviewModel:
        """Create a review."""
        return ReviewModel.objects.create(
            danawa_product_id=danawa_product_id,
            user_id=user_id,
            content=content,
            rating=rating,
            mall_name=mall_name,
            reviewer_name=reviewer_name,
        )
