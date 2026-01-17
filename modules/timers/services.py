"""
Timers business logic services.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from django.db import transaction
from django.utils import timezone

from .models import TimerModel, PriceHistoryModel
from .exceptions import (
    PredictionNotFoundError,
    InsufficientHistoryDataError,
    PredictionServiceError,
)

logger = logging.getLogger(__name__)


class TimerService:
    """Service for timer operations."""

    def get_timer_by_id(self, timer_id: int) -> Optional[TimerModel]:
        """Get timer by ID."""
        try:
            return TimerModel.objects.get(
                id=timer_id,
                deleted_at__isnull=True
            )
        except TimerModel.DoesNotExist:
            return None

    def get_timer_by_product(
        self,
        danawa_product_id: str,
        prediction_date: Optional[datetime] = None
    ) -> Optional[TimerModel]:
        """Get latest timer for a product."""
        queryset = TimerModel.objects.filter(
            danawa_product_id=danawa_product_id,
            deleted_at__isnull=True
        )
        if prediction_date:
            queryset = queryset.filter(prediction_date=prediction_date)
        return queryset.order_by('-created_at').first()

    def get_timers_for_product(
        self,
        danawa_product_id: str,
        days: int = 7
    ) -> List[TimerModel]:
        """Get timers for next N days."""
        today = timezone.now()
        end_date = today + timedelta(days=days)
        return list(
            TimerModel.objects.filter(
                danawa_product_id=danawa_product_id,
                prediction_date__gte=today,
                prediction_date__lte=end_date,
                deleted_at__isnull=True
            ).order_by('prediction_date')
        )

    def get_user_timers(
        self,
        user_id: int,
        is_notification_enabled: bool = None,
        offset: int = 0,
        limit: int = 20
    ) -> List[TimerModel]:
        """Get timers for a user."""
        queryset = TimerModel.objects.filter(
            user_id=user_id,
            deleted_at__isnull=True
        )
        if is_notification_enabled is not None:
            queryset = queryset.filter(is_notification_enabled=is_notification_enabled)
        return list(queryset.order_by('-created_at')[offset:offset + limit])

    @transaction.atomic
    def create_timer(
        self,
        danawa_product_id: str,
        user_id: int,
        target_price: int,
        prediction_date: datetime,
        model_version: str = 'v1.0'
    ) -> TimerModel:
        """Create a new price timer using AI."""
        # Get historical data
        history = self._get_price_history(danawa_product_id)

        # Calculate prediction
        predicted_price, confidence, suitability_score, guide_message = self._calculate_prediction(
            target_price,
            history,
            prediction_date
        )

        timer = TimerModel.objects.create(
            danawa_product_id=danawa_product_id,
            user_id=user_id,
            target_price=target_price,
            predicted_price=predicted_price,
            prediction_date=prediction_date,
            confidence_score=confidence,
            purchase_suitability_score=suitability_score,
            purchase_guide_message=guide_message,
            is_notification_enabled=True
        )

        logger.info(
            f"Created timer for product {danawa_product_id}: "
            f"{target_price} -> {predicted_price}"
        )
        return timer

    @transaction.atomic
    def update_timer(
        self,
        timer_id: int,
        is_notification_enabled: bool = None,
    ) -> TimerModel:
        """Update a timer."""
        timer = self.get_timer_by_id(timer_id)
        if not timer:
            raise PredictionNotFoundError(str(timer_id))

        if is_notification_enabled is not None:
            timer.is_notification_enabled = is_notification_enabled

        timer.save()
        return timer

    @transaction.atomic
    def delete_timer(self, timer_id: int) -> bool:
        """Soft delete a timer."""
        timer = self.get_timer_by_id(timer_id)
        if not timer:
            return False

        timer.deleted_at = timezone.now()
        timer.is_notification_enabled = False
        timer.save()
        return True

    @transaction.atomic
    def record_price_history(
        self,
        danawa_product_id: str,
        lowest_price: int,
    ) -> PriceHistoryModel:
        """Record a price point for historical tracking."""
        return PriceHistoryModel.objects.create(
            danawa_product_id=danawa_product_id,
            lowest_price=lowest_price,
            recorded_at=timezone.now(),
        )

    def get_price_history(
        self,
        danawa_product_id: str,
        days: int = 30
    ) -> List[PriceHistoryModel]:
        """Get price history for a product."""
        start_date = timezone.now() - timedelta(days=days)
        return list(
            PriceHistoryModel.objects.filter(
                danawa_product_id=danawa_product_id,
                recorded_at__gte=start_date,
                deleted_at__isnull=True
            ).order_by('recorded_at')
        )

    def get_price_trend(
        self,
        danawa_product_id: str,
        days: int = 30
    ) -> dict:
        """Analyze price trend for a product."""
        start_date = timezone.now() - timedelta(days=days)
        history = PriceHistoryModel.objects.filter(
            danawa_product_id=danawa_product_id,
            recorded_at__gte=start_date,
            deleted_at__isnull=True
        ).order_by('recorded_at')

        if not history.exists():
            return {
                'trend': 'unknown',
                'change_percent': 0,
                'data_points': 0
            }

        prices = [h.lowest_price for h in history]
        first_price = prices[0]
        last_price = prices[-1]

        change_percent = ((last_price - first_price) / first_price) * 100 if first_price > 0 else 0

        if change_percent > 5:
            trend = 'increasing'
        elif change_percent < -5:
            trend = 'decreasing'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'change_percent': round(change_percent, 2),
            'data_points': len(prices),
            'min_price': min(prices),
            'max_price': max(prices),
            'avg_price': round(sum(prices) / len(prices), 2)
        }

    def _get_price_history(
        self,
        danawa_product_id: str,
        days: int = 30
    ) -> List[PriceHistoryModel]:
        """Get price history for prediction."""
        start_date = timezone.now() - timedelta(days=days)
        return list(
            PriceHistoryModel.objects.filter(
                danawa_product_id=danawa_product_id,
                recorded_at__gte=start_date,
                deleted_at__isnull=True
            ).order_by('recorded_at')
        )

    def _calculate_prediction(
        self,
        target_price: int,
        history: List[PriceHistoryModel],
        prediction_date: datetime
    ) -> tuple:
        """
        Calculate predicted price and purchase guidance.

        TODO: Replace with actual ML model (e.g., LSTM, Prophet)
        This is a simplified moving average approach.
        """
        if not history:
            # No history, use target price as base
            return target_price, 0.5, 50, "가격 이력이 부족합니다. 더 많은 데이터가 필요합니다."

        prices = [h.lowest_price for h in history[-7:]] if len(history) >= 7 else [h.lowest_price for h in history]
        avg_price = sum(prices) / len(prices)

        # Simple trend calculation
        if len(prices) >= 3:
            recent_avg = sum(prices[-3:]) / 3
            older_avg = sum(prices[:3]) / 3 if len(prices) >= 6 else prices[0]
            trend_factor = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
        else:
            trend_factor = 0

        # Days until prediction
        days_ahead = (prediction_date.date() - timezone.now().date()).days
        predicted = int(avg_price * (1 + trend_factor * days_ahead * 0.1))

        # Confidence decreases with time
        confidence = max(0.5, 0.95 - (days_ahead * 0.05))

        # Calculate purchase suitability score (0-100)
        if predicted <= target_price:
            suitability_score = min(100, int(80 + (target_price - predicted) / target_price * 100))
            guide_message = "예측 가격이 목표가보다 낮습니다. 구매를 권장합니다."
        else:
            suitability_score = max(0, int(50 - (predicted - target_price) / target_price * 100))
            guide_message = "예측 가격이 목표가보다 높습니다. 좀 더 기다려보세요."

        return predicted, confidence, suitability_score, guide_message


class PriceHistoryService:
    """Service for price history operations."""

    def get_history_by_product(
        self,
        danawa_product_id: str,
        days: int = 30
    ) -> List[PriceHistoryModel]:
        """Get price history for a product."""
        start_date = timezone.now() - timedelta(days=days)
        return list(
            PriceHistoryModel.objects.filter(
                danawa_product_id=danawa_product_id,
                recorded_at__gte=start_date,
                deleted_at__isnull=True
            ).order_by('-recorded_at')
        )

    @transaction.atomic
    def create_history(
        self,
        danawa_product_id: str,
        lowest_price: int,
    ) -> PriceHistoryModel:
        """Create a new price history record."""
        return PriceHistoryModel.objects.create(
            danawa_product_id=danawa_product_id,
            lowest_price=lowest_price,
            recorded_at=timezone.now(),
        )

    @transaction.atomic
    def delete_history(self, history_id: int) -> bool:
        """Soft delete a price history record."""
        try:
            history = PriceHistoryModel.objects.get(
                id=history_id,
                deleted_at__isnull=True
            )
            history.deleted_at = timezone.now()
            history.save()
            return True
        except PriceHistoryModel.DoesNotExist:
            return False
