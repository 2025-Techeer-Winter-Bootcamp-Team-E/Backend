"""
Timers URL configuration.
"""
from django.urls import path

from .views import TimerListCreateView

app_name = 'timers'

urlpatterns = [
    path('', TimerListCreateView.as_view(), name='timer-list-create'),
]
