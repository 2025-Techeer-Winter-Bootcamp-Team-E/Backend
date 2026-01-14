"""
Orders API v1 URLs.
"""
from django.urls import path

from .views import (
    CartView,
    CartItemView,
    OrderListCreateView,
    OrderDetailView,
)

urlpatterns = [
    # Cart
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/items/<uuid:product_id>/', CartItemView.as_view(), name='cart-item'),

    # Orders
    path('', OrderListCreateView.as_view(), name='order-list-create'),
    path('<uuid:order_id>/', OrderDetailView.as_view(), name='order-detail'),
]
