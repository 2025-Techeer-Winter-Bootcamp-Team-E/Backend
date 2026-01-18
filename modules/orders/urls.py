"""
Orders module URLs.
"""
from django.urls import path

from .views import TokenRechargeView, TokenBalanceView, TokenPurchaseView

urlpatterns = [
    path('tokens/recharge/', TokenRechargeView.as_view(), name='token-recharge'),
    path('tokens/', TokenBalanceView.as_view(), name='token-balance'),
    path('purchase/', TokenPurchaseView.as_view(), name='token-purchase'),
]
