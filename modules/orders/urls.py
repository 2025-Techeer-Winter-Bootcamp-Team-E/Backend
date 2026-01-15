"""
Orders module URLs.
"""
from django.urls import path

from .views import (
    StorageListView,
    StorageItemView,
    PurchaseListCreateView,
    PurchaseDetailView,
    TokenHistoryListView,
    ReviewListCreateView,
    ProductReviewListView,
)

urlpatterns = [
    # Storage (장바구니)
    path('storage/', StorageListView.as_view(), name='storage-list'),
    path('storage/<int:product_id>/', StorageItemView.as_view(), name='storage-item'),

    # Purchase (구매)
    path('purchases/', PurchaseListCreateView.as_view(), name='purchase-list'),
    path('purchases/<int:purchase_id>/', PurchaseDetailView.as_view(), name='purchase-detail'),

    # Token History
    path('token-histories/', TokenHistoryListView.as_view(), name='token-history-list'),

    # Reviews
    path('reviews/', ReviewListCreateView.as_view(), name='review-list'),
    path('reviews/product/<int:product_id>/', ProductReviewListView.as_view(), name='product-review-list'),
]
