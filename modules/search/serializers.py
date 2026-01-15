"""
Search serializers.
"""
from rest_framework import serializers

from .models import SearchModel, RecentViewModel


class SearchQuerySerializer(serializers.Serializer):
    """Serializer for search request."""

    query = serializers.CharField(
        min_length=2,
        max_length=500,
        help_text='Search query text'
    )
    search_mode = serializers.ChoiceField(
        choices=['basic', 'llm', 'shopping_research'],
        default='basic',
        help_text='Type of search to perform'
    )
    category_id = serializers.IntegerField(
        required=False,
        help_text='Filter by category'
    )
    page = serializers.IntegerField(
        min_value=1,
        default=1,
        help_text='Page number'
    )
    page_size = serializers.IntegerField(
        min_value=1,
        max_value=100,
        default=20,
        help_text='Results per page'
    )


class SearchResultSerializer(serializers.Serializer):
    """Serializer for search results."""

    results = serializers.ListField(
        help_text='List of product results'
    )
    total = serializers.IntegerField(
        help_text='Total number of results'
    )
    query = serializers.CharField()
    search_mode = serializers.CharField()


class SearchHistorySerializer(serializers.ModelSerializer):
    """Serializer for search history."""

    class Meta:
        model = SearchModel
        fields = [
            'id',
            'query',
            'search_mode',
            'searched_at',
            'danawa_product_id',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class RecentViewSerializer(serializers.ModelSerializer):
    """Serializer for recent views."""

    class Meta:
        model = RecentViewModel
        fields = [
            'id',
            'product_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecentViewCreateSerializer(serializers.Serializer):
    """Serializer for creating recent view."""

    product_id = serializers.IntegerField()
