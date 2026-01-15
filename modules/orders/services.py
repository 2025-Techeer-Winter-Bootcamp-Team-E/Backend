"""
Orders module service layer.
"""
from datetime import datetime
from typing import Optional, List

from django.db import transaction

from .models import (
    StorageModel,
    PurchaseModel,
    PurchaseItemModel,
    TokenHistoryModel,
    ReviewModel,
)
from .exceptions import (
    OrderNotFoundError,
    CartNotFoundError,
    EmptyCartError,
)


class StorageService:
    """
    Storage (장바구니) business logic service.
    """

    def get_user_storage_items(self, user_id: int) -> List[StorageModel]:
        """Get all storage items for a user."""
        return list(
            StorageModel.objects.filter(user_id=user_id, deleted_at__isnull=True)
            .select_related('product')
        )

    def add_item(
        self,
        user_id: int,
        product_id: int,
        quantity: int = 1,
    ) -> StorageModel:
        """Add item to storage."""
        storage_item, created = StorageModel.objects.get_or_create(
            user_id=user_id,
            product_id=product_id,
            defaults={'quantity': quantity}
        )

        if not created:
            storage_item.quantity += quantity
            storage_item.save()

        return storage_item

    def update_item_quantity(
        self,
        user_id: int,
        product_id: int,
        quantity: int,
    ) -> Optional[StorageModel]:
        """Update storage item quantity."""
        try:
            storage_item = StorageModel.objects.get(
                user_id=user_id,
                product_id=product_id,
                deleted_at__isnull=True
            )
            if quantity <= 0:
                storage_item.deleted_at = datetime.now()
                storage_item.save()
                return None
            else:
                storage_item.quantity = quantity
                storage_item.save()
                return storage_item
        except StorageModel.DoesNotExist:
            raise CartNotFoundError(f"User {user_id}")

    def remove_item(self, user_id: int, product_id: int) -> bool:
        """Remove item from storage (soft delete)."""
        try:
            storage_item = StorageModel.objects.get(
                user_id=user_id,
                product_id=product_id,
                deleted_at__isnull=True
            )
            storage_item.deleted_at = datetime.now()
            storage_item.save()
            return True
        except StorageModel.DoesNotExist:
            return False

    def clear_storage(self, user_id: int) -> bool:
        """Clear all items from storage (soft delete)."""
        StorageModel.objects.filter(
            user_id=user_id,
            deleted_at__isnull=True
        ).update(deleted_at=datetime.now())
        return True


class PurchaseService:
    """
    Purchase business logic service.
    """

    def __init__(self):
        self.storage_service = StorageService()

    def get_purchase_by_id(self, purchase_id: int) -> Optional[PurchaseModel]:
        """Get purchase by ID."""
        try:
            return PurchaseModel.objects.prefetch_related('items').get(
                id=purchase_id,
                deleted_at__isnull=True
            )
        except PurchaseModel.DoesNotExist:
            return None

    def get_user_purchases(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> List[PurchaseModel]:
        """Get all purchases for a user."""
        return list(
            PurchaseModel.objects.filter(user_id=user_id, deleted_at__isnull=True)
            .prefetch_related('items')
            .order_by('-created_at')[offset:offset + limit]
        )

    @transaction.atomic
    def create_purchase_from_storage(self, user_id: int) -> PurchaseModel:
        """Create purchase from user's storage items."""
        storage_items = self.storage_service.get_user_storage_items(user_id)
        if not storage_items:
            raise EmptyCartError()

        # Create purchase
        purchase = PurchaseModel.objects.create(user_id=user_id)

        # Create purchase items from storage items
        for storage_item in storage_items:
            PurchaseItemModel.objects.create(
                purchase=purchase,
                product=storage_item.product,
                quantity=storage_item.quantity,
            )

        # Clear the storage
        self.storage_service.clear_storage(user_id)

        return purchase


class TokenHistoryService:
    """
    Token history business logic service.
    """

    def get_user_token_histories(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> List[TokenHistoryModel]:
        """Get token histories for a user."""
        return list(
            TokenHistoryModel.objects.filter(user_id=user_id, deleted_at__isnull=True)
            .order_by('-transaction_at')[offset:offset + limit]
        )

    def create_token_history(
        self,
        user_id: int,
        transaction_type: str,
        token_change: int,
        token_balance_after: int,
        danawa_product_id: str,
        token_owner_id: int = None,
    ) -> TokenHistoryModel:
        """Create a token history record."""
        return TokenHistoryModel.objects.create(
            user_id=user_id,
            transaction_type=transaction_type,
            token_change=token_change,
            token_balance_after=token_balance_after,
            token_owner_id=token_owner_id,
            transaction_at=datetime.now(),
            danawa_product_id=danawa_product_id,
        )


class ReviewService:
    """
    Review business logic service.
    """

    def get_product_reviews(
        self,
        product_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ReviewModel]:
        """Get reviews for a product."""
        return list(
            ReviewModel.objects.filter(product_id=product_id, deleted_at__isnull=True)
            .order_by('-created_at')[offset:offset + limit]
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
        product_id: int,
        user_id: int,
        content: str = None,
        rating: int = None,
        mall_name: str = None,
        reviewer_name: str = None,
    ) -> ReviewModel:
        """Create a review."""
        return ReviewModel.objects.create(
            product_id=product_id,
            user_id=user_id,
            content=content,
            rating=rating,
            mall_name=mall_name,
            reviewer_name=reviewer_name,
        )
