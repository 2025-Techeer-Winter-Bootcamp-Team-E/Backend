from django.urls import path
from .views import ProductPriceTrendView,ProductDetailView,ProductMallInfoView
urlpatterns = [
    path('products/<int:product_id>/price-trend/',ProductPriceTrendView.as_view(), name='product-price-trend'),
    path('products/<int:product_id>/',ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:product_id>/prices/',ProductMallInfoView.as_view(), name='product-mall_info')
    ]

