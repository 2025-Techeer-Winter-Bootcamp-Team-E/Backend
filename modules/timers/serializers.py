"""
Price Prediction serializers.
"""
from rest_framework import serializers

from .models import PricePredictionModel, PriceHistoryModel


class PricePredictionSerializer(serializers.ModelSerializer):
    """Serializer for price prediction."""

    price_change = serializers.SerializerMethodField()
    change_percent = serializers.SerializerMethodField()

    class Meta:
        model = PricePredictionModel
        fields = [
            'id',
            'product',
            'user',
            'target_price',
            'predicted_price',
            'prediction_date',
            'confidence_score',
            'purchase_suitability_score',
            'purchase_guide_message',
            'is_active',
            'price_change',
            'change_percent',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_price_change(self, obj):
        """Calculate absolute price change."""
        if obj.target_price and obj.predicted_price:
            return obj.predicted_price - obj.target_price
        return 0

    def get_change_percent(self, obj):
        """Calculate percentage change."""
        if not obj.target_price or obj.target_price == 0:
            return 0
        change = (obj.predicted_price - obj.target_price) / obj.target_price * 100
        return round(float(change), 2)


class PricePredictionCreateSerializer(serializers.Serializer):
    """Serializer for creating prediction request."""

    product_id = serializers.IntegerField()
    target_price = serializers.IntegerField(min_value=0)
    prediction_days = serializers.IntegerField(
        min_value=1,
        max_value=30,
        default=7,
        help_text='Number of days to predict'
    )


class PricePredictionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for prediction list."""

    class Meta:
        model = PricePredictionModel
        fields = [
            'id',
            'product',
            'target_price',
            'predicted_price',
            'prediction_date',
            'confidence_score',
            'purchase_suitability_score',
            'is_active',
            'created_at',
        ]


class PriceHistorySerializer(serializers.ModelSerializer):
    """Serializer for price history."""

    class Meta:
        model = PriceHistoryModel
        fields = [
            'id',
            'product',
            'lowest_price',
            'recorded_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PriceHistoryCreateSerializer(serializers.Serializer):
    """Serializer for creating price history."""

    product_id = serializers.IntegerField()
    lowest_price = serializers.IntegerField(min_value=0)


class PriceTrendSerializer(serializers.Serializer):
    """Serializer for price trend analysis."""

    trend = serializers.CharField()
    change_percent = serializers.FloatField()
    data_points = serializers.IntegerField()
    min_price = serializers.IntegerField(required=False)
    max_price = serializers.IntegerField(required=False)
    avg_price = serializers.FloatField(required=False)
