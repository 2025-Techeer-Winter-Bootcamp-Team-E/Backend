"""
Timers module configuration.
가격 예측 및 가격 알림 관련 기능.
"""
from django.apps import AppConfig


class TimersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.timers'
    verbose_name = 'Timers'

    def ready(self):
        pass
