"""
Orders module URLs.
"""
from django.urls import path

from .views import (
    TokenRechargeView,
    TokenBalanceView,
    TokenPurchaseView,
    CartItemListCreateView,
    CartItemDetailView, # Changed from CartItemDeleteView
    CartPaymentView,
)

urlpatterns = [
    path('tokens/recharge/', TokenRechargeView.as_view(), name='token-recharge'),
    path('tokens/', TokenBalanceView.as_view(), name='token-balance'),
    path('purchase/', TokenPurchaseView.as_view(), name='token-purchase'),
    path('cart/checkout/', CartPaymentView.as_view(), name='cart-payment'),
    path('cart/<int:cart_item_id>/', CartItemDetailView.as_view(), name='cart-item-detail'), # Handles both PATCH and DELETE
    path('cart/', CartItemListCreateView.as_view(), name='cart-items'),
]
