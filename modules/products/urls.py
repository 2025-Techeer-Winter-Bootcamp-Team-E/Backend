from django.urls import path
from .views import ProductPriceTrendView,ProductDetailView,ProductMallInfoView
urlpatterns = [
    path('products/<str:product_code>/price-trend/',ProductPriceTrendView.as_view(), name='product-price-trend'),
    path('products/<str:product_code>/',ProductDetailView.as_view(), name='product_detail'),
    path('products/<str:product_code>/prices/',ProductMallInfoView.as_view(), name='product-mall_info')
    ]

