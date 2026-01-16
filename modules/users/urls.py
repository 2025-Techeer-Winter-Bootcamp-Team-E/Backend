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
)

urlpatterns = [
    
    

    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # User
    
    path('me/', UserMeView.as_view(), name='user-me'),
    path('', UserListView.as_view(), name='user-list'),
    path('<int:user_id>/', UserDetailView.as_view(), name='user-detail'),
    path('<int:user_id>/token-balance/', UserTokenBalanceView.as_view(), name='user-token-balance'),
    
    path('signup/', SignupView.as_view(), name='user-signup'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('social-login/', SocialLoginView.as_view(), name='user-social-login'),

]
