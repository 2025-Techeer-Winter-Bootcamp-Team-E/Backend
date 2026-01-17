"""
Users module URLs.
"""
from django.urls import path

from .views import (
    SignupView,
    LoginView,
)

urlpatterns = [
    path('signup/', SignupView.as_view(), name='user-signup'),
    path('login/', LoginView.as_view(), name='user-login'),
]
