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
    RecentlyViewedProductsView,
    FavoriteProductsView,
    CartListView,
    PurchaseTimersView,
)

urlpatterns = [
    
    

    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # User
    
    
    
    path('signup/', SignupView.as_view(), name='user-signup'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('social-login/', SocialLoginView.as_view(), name='user-social-login'),
    path('password/', PasswordChangeView.as_view()),
    path('me/', UserDeleteView.as_view(), name='user-delete'),
    path('recent-products/', RecentlyViewedProductsView.as_view(), name='recently-viewed-products'),
    path('wishlist/', FavoriteProductsView.as_view(), name='favorite-products'),
    path('cart/', CartListView.as_view(), name='user-cart'),
    path('timers/', PurchaseTimersView.as_view(), name='purchase-timers'),
]
