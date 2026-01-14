"""
Products admin configuration.
"""
from django.contrib import admin

from ..infrastructure.models.product_model import ProductModel
from ..infrastructure.models.category_model import CategoryModel


@admin.register(ProductModel)
class ProductAdmin(admin.ModelAdmin):
    """Admin configuration for Product model."""
    list_display = ('name', 'sku', 'price', 'stock_quantity', 'is_active', 'created_at')
    list_filter = ('is_active', 'currency', 'created_at')
    search_fields = ('name', 'sku', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(CategoryModel)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Category model."""
    list_display = ('name', 'parent', 'is_active', 'created_at')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'description')
    ordering = ('name',)
    readonly_fields = ('id', 'created_at', 'updated_at')
