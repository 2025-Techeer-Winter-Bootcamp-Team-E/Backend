"""
Search admin configuration.
"""
from django.contrib import admin

from .models import SearchModel, RecentViewModel


@admin.register(SearchModel)
class SearchAdmin(admin.ModelAdmin):
    """Admin for search history."""

    list_display = [
        'id',
        'query',
        'search_mode',
        'searched_at',
        'user',
        'danawa_product_id',
        'created_at',
    ]
    list_filter = ['search_mode', 'searched_at', 'created_at']
    search_fields = ['query', 'danawa_product_id', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-searched_at']


@admin.register(RecentViewModel)
class RecentViewAdmin(admin.ModelAdmin):
    """Admin for recent views."""

    list_display = [
        'id',
        'user',
        'product',
        'created_at',
        'updated_at',
    ]
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__email', 'product__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-updated_at']
