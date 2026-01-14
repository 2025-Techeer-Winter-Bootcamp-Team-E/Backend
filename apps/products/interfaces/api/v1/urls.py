"""
Products API v1 URLs.
"""
from django.urls import path

from .views import (
    ProductListCreateView,
    ProductDetailView,
    ProductSearchView,
    CategoryListCreateView,
    CategoryDetailView,
)

urlpatterns = [
    # Products
    path('', ProductListCreateView.as_view(), name='product-list-create'),
    path('<uuid:product_id>/', ProductDetailView.as_view(), name='product-detail'),
    path('search/', ProductSearchView.as_view(), name='product-search'),

    # Categories
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<uuid:category_id>/', CategoryDetailView.as_view(), name='category-detail'),
]
