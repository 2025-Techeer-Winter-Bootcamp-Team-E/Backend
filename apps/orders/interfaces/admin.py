"""
Orders admin configuration.
"""
from django.contrib import admin

from ..infrastructure.models.order_model import OrderModel, OrderItemModel
from ..infrastructure.models.cart_model import CartModel, CartItemModel


class OrderItemInline(admin.TabularInline):
    """Inline for order items."""
    model = OrderItemModel
    extra = 0
    readonly_fields = ('id', 'product_id', 'product_name', 'product_sku', 'quantity', 'unit_price')


@admin.register(OrderModel)
class OrderAdmin(admin.ModelAdmin):
    """Admin configuration for Order model."""
    list_display = ('order_number', 'user_id', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'user_id', 'recipient_name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'order_number', 'created_at', 'updated_at')
    inlines = [OrderItemInline]


class CartItemInline(admin.TabularInline):
    """Inline for cart items."""
    model = CartItemModel
    extra = 0


@admin.register(CartModel)
class CartAdmin(admin.ModelAdmin):
    """Admin configuration for Cart model."""
    list_display = ('id', 'user_id', 'created_at', 'updated_at')
    search_fields = ('user_id',)
    ordering = ('-updated_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [CartItemInline]
