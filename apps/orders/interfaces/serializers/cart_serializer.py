"""
Cart serializers.
"""
from rest_framework import serializers


class CartItemSerializer(serializers.Serializer):
    """Serializer for cart item output."""
    id = serializers.UUIDField(read_only=True)
    product_id = serializers.UUIDField(read_only=True)
    product_name = serializers.CharField(read_only=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)


class CartSerializer(serializers.Serializer):
    """Serializer for cart output."""
    id = serializers.UUIDField(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)


class CartItemCreateSerializer(serializers.Serializer):
    """Serializer for adding item to cart."""
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class CartItemUpdateSerializer(serializers.Serializer):
    """Serializer for updating cart item."""
    quantity = serializers.IntegerField(min_value=0)
