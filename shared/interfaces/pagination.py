"""
Custom pagination classes.
"""
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Standard pagination with configurable page size."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class SmallPagination(PageNumberPagination):
    """Small pagination for lightweight lists."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class LargePagination(PageNumberPagination):
    """Large pagination for bulk operations."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
