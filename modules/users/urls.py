"""
Users module URLs.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    SignupView,
    RegisterView,
    LoginView,
    SocialLoginView,
    UserMeView,
    UserListView,
    UserDetailView,
    UserTokenBalanceView,
    PasswordChangeView,
    UserDeleteView,
)

urlpatterns = [
    
    

    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # User
    
    
    
    path('signup/', SignupView.as_view(), name='user-signup'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('social-login/', SocialLoginView.as_view(), name='user-social-login'),
    path('password/', PasswordChangeView.as_view()),
    path('me/', UserDeleteView.as_view(), name='user-delete'),

]
