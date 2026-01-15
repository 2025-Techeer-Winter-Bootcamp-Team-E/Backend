"""
Products module URLs.
"""
from django.urls import path

from .views import (
    ProductListCreateView,
    ProductDetailView,
    ProductSearchView,
    ProductMallInfoView,
)

urlpatterns = [
    path('', ProductListCreateView.as_view(), name='product-list'),
    path('search/', ProductSearchView.as_view(), name='product-search'),
    path('<int:product_id>/', ProductDetailView.as_view(), name='product-detail'),
    path('<int:product_id>/mall-info/', ProductMallInfoView.as_view(), name='product-mall-info'),
]
