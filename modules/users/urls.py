from django.urls import path
from .views import UserSignupView, UserLoginview

urlpatterns = [
    path('signup/', UserSignupView.as_view(), name='user-signup'),
    path('login/', UserLoginview.as_view(), name='user-login'),
]