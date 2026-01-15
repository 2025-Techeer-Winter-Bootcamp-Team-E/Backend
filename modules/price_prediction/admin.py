"""
Price Prediction admin configuration.
"""
from django.contrib import admin

from .models import PricePredictionModel, PriceHistoryModel


@admin.register(PricePredictionModel)
class PricePredictionAdmin(admin.ModelAdmin):
    """Admin for price predictions."""

    list_display = [
        'id',
        'product',
        'user',
        'target_price',
        'predicted_price',
        'prediction_date',
        'confidence_score',
        'is_active',
        'created_at',
    ]
    list_filter = ['prediction_date', 'is_active', 'created_at']
    search_fields = ['product__name', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(PriceHistoryModel)
class PriceHistoryAdmin(admin.ModelAdmin):
    """Admin for price history."""

    list_display = [
        'id',
        'product',
        'lowest_price',
        'recorded_at',
        'created_at',
    ]
    list_filter = ['recorded_at', 'created_at']
    search_fields = ['product__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-recorded_at']
