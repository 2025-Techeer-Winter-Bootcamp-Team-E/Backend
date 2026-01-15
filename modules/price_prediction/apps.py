"""
Price Prediction module configuration.
"""
from django.apps import AppConfig


class PricePredictionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.price_prediction'
    verbose_name = 'Price Prediction'

    def ready(self):
        pass
