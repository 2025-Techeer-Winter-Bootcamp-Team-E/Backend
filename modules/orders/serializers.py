"""
Orders module serializers.
"""
from rest_framework import serializers


# Storage (장바구니) Serializers

class StorageItemSerializer(serializers.Serializer):
    """Serializer for storage item output."""
    id = serializers.IntegerField(read_only=True)
    product_id = serializers.IntegerField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class StorageItemCreateSerializer(serializers.Serializer):
    """Serializer for adding item to storage."""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class StorageItemUpdateSerializer(serializers.Serializer):
    """Serializer for updating storage item."""
    quantity = serializers.IntegerField(min_value=0)


# Purchase Serializers

class PurchaseItemSerializer(serializers.Serializer):
    """Serializer for purchase item output."""
    id = serializers.IntegerField(read_only=True)
    purchase_id = serializers.IntegerField(read_only=True)
    product_id = serializers.IntegerField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class PurchaseSerializer(serializers.Serializer):
    """Serializer for purchase output."""
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    items = PurchaseItemSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


# Token History Serializers

class TokenHistorySerializer(serializers.Serializer):
    """Serializer for token history output."""
    id = serializers.IntegerField(read_only=True)
    transaction_type = serializers.CharField(read_only=True)
    token_change = serializers.IntegerField(read_only=True)
    token_balance_after = serializers.IntegerField(read_only=True)
    transaction_at = serializers.DateTimeField(read_only=True)
    danawa_product_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


# Review Serializers

class ReviewSerializer(serializers.Serializer):
    """Serializer for review output."""
    id = serializers.IntegerField(read_only=True)
    product_id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    mall_name = serializers.CharField(read_only=True, allow_null=True)
    reviewer_name = serializers.CharField(read_only=True, allow_null=True)
    content = serializers.CharField(read_only=True, allow_null=True)
    rating = serializers.IntegerField(read_only=True, allow_null=True)
    ai_review_summary = serializers.JSONField(read_only=True, allow_null=True)
    external_review_count = serializers.IntegerField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)


class ReviewCreateSerializer(serializers.Serializer):
    """Serializer for creating a review."""
    product_id = serializers.IntegerField()
    content = serializers.CharField(required=False, allow_blank=True)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    mall_name = serializers.CharField(required=False, allow_blank=True)
    reviewer_name = serializers.CharField(required=False, allow_blank=True)
