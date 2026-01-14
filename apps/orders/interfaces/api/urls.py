"""
Orders API URLs.
"""
from django.urls import path, include

urlpatterns = [
    path('', include('apps.orders.interfaces.api.v1.urls')),
]
