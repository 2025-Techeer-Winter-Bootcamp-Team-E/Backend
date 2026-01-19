from django.urls import path
from .views import (
    ProductListCreateView,
    ProductDetailView,
    ProductMallInfoView,
    ProductPriceTrendView
)

urlpatterns = [
    
    path('products/', ProductListCreateView.as_view(), name='product-list'),#이 path는 명세서에 없는 기능(수정전에 작성되어 있던 기능인데, 메인페이지 불러올 때 필요해 보임)
    path('products/<int:product_id>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<int:product_id>/price-trend/', ProductPriceTrendView.as_view(), name='product-price-trend'),
    path('products/<int:product_id>/prices/', ProductMallInfoView.as_view(), name='product-mall-info'),
]