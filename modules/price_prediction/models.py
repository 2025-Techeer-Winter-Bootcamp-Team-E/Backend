"""
Price Prediction models based on ERD.
"""
from django.db import models


class PricePredictionModel(models.Model):
    """Price prediction record model."""

    target_price = models.IntegerField(
        verbose_name='목표가'
    )
    predicted_price = models.IntegerField(
        verbose_name='예측가격'
    )
    prediction_date = models.DateTimeField(
        verbose_name='예측일자'
    )
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name='신뢰도'
    )
    purchase_suitability_score = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='구매적합도점수'
    )
    purchase_guide_message = models.TextField(
        null=True,
        blank=True,
        verbose_name='구매가이드메시지'
    )
    is_active = models.BooleanField(
        null=True,
        blank=True,
        verbose_name='활성화여부'
    )
    product = models.ForeignKey(
        'products.ProductModel',
        on_delete=models.CASCADE,
        related_name='price_predictions',
        verbose_name='상품번호'
    )
    user = models.ForeignKey(
        'users.UserModel',
        on_delete=models.CASCADE,
        related_name='price_predictions',
        verbose_name='회원번호'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성시각'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정시각'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='논리적삭제플래그'
    )

    class Meta:
        db_table = 'price_predictions'
        verbose_name = 'Price Prediction'
        verbose_name_plural = 'Price Predictions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'prediction_date']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"Prediction for product {self.product_id}: {self.predicted_price}"

    @property
    def is_deleted(self) -> bool:
        """Check if prediction is soft deleted."""
        return self.deleted_at is not None


class PriceHistoryModel(models.Model):
    """Historical price data."""

    recorded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='기록일시'
    )
    lowest_price = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='최저가'
    )
    product = models.ForeignKey(
        'products.ProductModel',
        on_delete=models.CASCADE,
        related_name='price_histories',
        verbose_name='상품번호'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성시각'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정시각'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='논리적삭제플래그'
    )

    class Meta:
        db_table = 'price_histories'
        verbose_name = 'Price History'
        verbose_name_plural = 'Price Histories'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['product', 'recorded_at']),
        ]

    def __str__(self):
        return f"{self.product_id}: {self.lowest_price} at {self.recorded_at}"

    @property
    def is_deleted(self) -> bool:
        """Check if price history is soft deleted."""
        return self.deleted_at is not None
