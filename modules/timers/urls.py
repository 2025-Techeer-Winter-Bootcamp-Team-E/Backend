"""
Price Prediction URL configuration.
"""
from django.urls import path

from .views import (
    PredictionListCreateView,
    PredictionDetailView,
    PriceTrendView,
    PriceHistoryListCreateView,
)

app_name = 'price_prediction'

urlpatterns = [
    path('predictions/', PredictionListCreateView.as_view(), name='prediction-list'),
    path('predictions/<int:prediction_id>/', PredictionDetailView.as_view(), name='prediction-detail'),
    path('trend/', PriceTrendView.as_view(), name='price-trend'),
    path('history/', PriceHistoryListCreateView.as_view(), name='price-history'),
]
