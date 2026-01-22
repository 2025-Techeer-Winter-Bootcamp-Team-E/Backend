from django.urls import path
from .views import (
    ProductListView,
    ProductPriceTrendView,
    ProductDetailView,
    ProductMallInfoView,
    ProductReviewListView,
)

urlpatterns = [
    # 상품 목록 조회 및 검색 (루트 경로)
    path('', ProductListView.as_view(), name='product-list'),
    # 기존 URL들
    path('products/<str:product_code>/price-trend/', ProductPriceTrendView.as_view(), name='product-price-trend'),
    path('products/<str:product_code>/', ProductDetailView.as_view(), name='product_detail'),
    path('products/<str:product_code>/prices/', ProductMallInfoView.as_view(), name='product-mall_info'),
    path('products/<str:product_code>/reviews/', ProductReviewListView.as_view(), name='product-review-list'),
]

