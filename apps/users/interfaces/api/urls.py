"""
Users API URLs.
"""
from django.urls import path, include

urlpatterns = [
    path('', include('apps.users.interfaces.api.v1.urls')),
]
