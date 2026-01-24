"""
Timers URL configuration.
"""
from django.urls import path
from .views import TimerListCreateView, TimerDetailView

app_name = 'timers'

urlpatterns = [
    path('', TimerListCreateView.as_view(), name='timer-list-create'),
    path('<int:timer_id>/', TimerDetailView.as_view(), name='timer-detail'),
]
