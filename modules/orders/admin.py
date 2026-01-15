"""
Orders module admin configuration.
"""
from django.contrib import admin

from .models import (
    StorageModel,
    PurchaseModel,
    PurchaseItemModel,
    TokenHistoryModel,
    ReviewModel,
)


class PurchaseItemInline(admin.TabularInline):
    """Inline admin for purchase items."""
    model = PurchaseItemModel
    extra = 0
    readonly_fields = ('product', 'quantity', 'created_at')


@admin.register(StorageModel)
class StorageAdmin(admin.ModelAdmin):
    """Admin configuration for Storage (장바구니) model."""
    list_display = ('id', 'user', 'product', 'quantity', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'product__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PurchaseModel)
class PurchaseAdmin(admin.ModelAdmin):
    """Admin configuration for Purchase model."""
    list_display = ('id', 'user', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('user__email',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PurchaseItemInline]


@admin.register(PurchaseItemModel)
class PurchaseItemAdmin(admin.ModelAdmin):
    """Admin configuration for Purchase Item model."""
    list_display = ('id', 'purchase', 'product', 'quantity', 'created_at')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TokenHistoryModel)
class TokenHistoryAdmin(admin.ModelAdmin):
    """Admin configuration for Token History model."""
    list_display = ('id', 'user', 'transaction_type', 'token_change', 'token_balance_after', 'transaction_at')
    list_filter = ('transaction_type', 'transaction_at')
    search_fields = ('user__email', 'danawa_product_id')
    ordering = ('-transaction_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ReviewModel)
class ReviewAdmin(admin.ModelAdmin):
    """Admin configuration for Review model."""
    list_display = ('id', 'product', 'user', 'reviewer_name', 'rating', 'mall_name', 'created_at')
    list_filter = ('rating', 'mall_name', 'created_at')
    search_fields = ('product__name', 'user__email', 'reviewer_name', 'content')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
