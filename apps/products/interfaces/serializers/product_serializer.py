"""
Product serializers.
"""
from rest_framework import serializers


class ProductSerializer(serializers.Serializer):
    """Serializer for product output."""
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    sku = serializers.CharField(read_only=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
    stock_quantity = serializers.IntegerField(read_only=True)
    category_id = serializers.UUIDField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    images = serializers.ListField(child=serializers.URLField(), read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ProductCreateSerializer(serializers.Serializer):
    """Serializer for product creation."""
    name = serializers.CharField(min_length=2, max_length=255)
    description = serializers.CharField()
    sku = serializers.CharField(min_length=3, max_length=100)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    currency = serializers.CharField(max_length=3, default='KRW')
    stock_quantity = serializers.IntegerField(min_value=0)
    category_id = serializers.UUIDField()
    images = serializers.ListField(child=serializers.URLField(), required=False)


class ProductUpdateSerializer(serializers.Serializer):
    """Serializer for product update."""
    name = serializers.CharField(min_length=2, max_length=255, required=False)
    description = serializers.CharField(required=False)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    currency = serializers.CharField(max_length=3, required=False)
