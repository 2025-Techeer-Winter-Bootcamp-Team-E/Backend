"""
Users API v1 URLs.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    LoginView,
    UserMeView,
    UserListView,
    UserDetailView,
)

urlpatterns = [
    # Auth
    path('register/', RegisterView.as_view(), name='user-register'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # User
    path('me/', UserMeView.as_view(), name='user-me'),
    path('', UserListView.as_view(), name='user-list'),
    path('<uuid:user_id>/', UserDetailView.as_view(), name='user-detail'),
]
