"""
Search URL configuration.
"""
from django.urls import path
from .views import (
    SearchView, 
    SearchHistoryView, 
    RecentViewProductsView, 
    RecentViewProductDeleteView,
    AutocompleteView
)
app_name = 'search'

urlpatterns = [
    path('', SearchView.as_view(), name='search'),
    path('history/', SearchHistoryView.as_view(), name='search-history'),
    path('recent-views/', RecentViewProductsView.as_view(), name='recent-views'),
    path('recent-views/<str:danawa_product_id>/', RecentViewProductDeleteView.as_view(), name='recent-view-delete'),
    
    # : 검색어 자동완성 
    path('autocomplete/', AutocompleteView.as_view(), name='autocomplete'),
]