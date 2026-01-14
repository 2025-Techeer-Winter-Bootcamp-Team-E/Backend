"""
Products API URLs.
"""
from django.urls import path, include

urlpatterns = [
    path('', include('apps.products.interfaces.api.v1.urls')),
]
