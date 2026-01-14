"""
Order serializers.
"""
from rest_framework import serializers


class OrderItemSerializer(serializers.Serializer):
    """Serializer for order item output."""
    id = serializers.UUIDField(read_only=True)
    product_id = serializers.UUIDField(read_only=True)
    product_name = serializers.CharField(read_only=True)
    product_sku = serializers.CharField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)


class ShippingInfoSerializer(serializers.Serializer):
    """Serializer for shipping information."""
    recipient_name = serializers.CharField(max_length=100)
    phone_number = serializers.CharField(max_length=20)
    address = serializers.CharField(max_length=255)
    address_detail = serializers.CharField(max_length=255, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=10, required=False, allow_blank=True)
    delivery_notes = serializers.CharField(required=False, allow_blank=True)


class OrderSerializer(serializers.Serializer):
    """Serializer for order output."""
    id = serializers.UUIDField(read_only=True)
    order_number = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    shipping_info = ShippingInfoSerializer(read_only=True)
    notes = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating an order."""
    shipping_info = ShippingInfoSerializer()
    notes = serializers.CharField(required=False, allow_blank=True)
