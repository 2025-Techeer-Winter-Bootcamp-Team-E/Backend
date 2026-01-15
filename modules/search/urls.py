"""
Search URL configuration.
"""
from django.urls import path

from .views import (
    SearchView,
    SearchHistoryView,
    RecentViewsView,
    RecentViewDeleteView,
)

app_name = 'search'

urlpatterns = [
    path('', SearchView.as_view(), name='search'),
    path('history/', SearchHistoryView.as_view(), name='history'),
    path('recent-views/', RecentViewsView.as_view(), name='recent-views'),
    path('recent-views/<int:product_id>/', RecentViewDeleteView.as_view(), name='recent-view-delete'),
]
