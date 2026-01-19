"""
Orders module URLs.
"""
from django.urls import path

from .views import (
    TokenRechargeView,
    TokenBalanceView,
    TokenPurchaseView,
    CartItemListCreateView,
    CartItemDeleteView,
    CartPaymentView,
)

urlpatterns = [
    path('tokens/recharge/', TokenRechargeView.as_view(), name='token-recharge'),
    path('tokens/', TokenBalanceView.as_view(), name='token-balance'),
    path('purchase/', TokenPurchaseView.as_view(), name='token-purchase'),
    path('cart/', CartItemListCreateView.as_view(), name='cart-items'),
    path('cart/<int:product_id>/', CartItemDeleteView.as_view(), name='cart-item-delete'),
    path('cart/checkout/', CartPaymentView.as_view(), name='cart-payment'),
]
