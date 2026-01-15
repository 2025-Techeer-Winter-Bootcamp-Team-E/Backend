"""
Orders module Django ORM models based on ERD.
"""
from django.db import models


class StorageModel(models.Model):
    """Shopping cart (장바구니) model."""

    quantity = models.IntegerField(
        verbose_name='수량'
    )
    product = models.ForeignKey(
        'products.ProductModel',
        on_delete=models.CASCADE,
        related_name='storage_items',
        verbose_name='상품번호'
    )
    user = models.ForeignKey(
        'users.UserModel',
        on_delete=models.CASCADE,
        related_name='storage_items',
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
        db_table = 'storages'
        verbose_name = 'Storage'
        verbose_name_plural = 'Storages'
        ordering = ['-created_at']
        unique_together = ['user', 'product']

    def __str__(self):
        return f"User {self.user_id} - Product {self.product_id} x {self.quantity}"

    @property
    def is_deleted(self) -> bool:
        """Check if storage item is soft deleted."""
        return self.deleted_at is not None


class PurchaseModel(models.Model):
    """Purchase (구매) model."""

    user = models.ForeignKey(
        'users.UserModel',
        on_delete=models.CASCADE,
        related_name='purchases',
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
        db_table = 'purchase'
        verbose_name = 'Purchase'
        verbose_name_plural = 'Purchases'
        ordering = ['-created_at']

    def __str__(self):
        return f"Purchase {self.id} by user {self.user_id}"

    @property
    def is_deleted(self) -> bool:
        """Check if purchase is soft deleted."""
        return self.deleted_at is not None


class PurchaseItemModel(models.Model):
    """Purchase item (구매 상품) model."""

    purchase = models.ForeignKey(
        PurchaseModel,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='구매번호'
    )
    product = models.ForeignKey(
        'products.ProductModel',
        on_delete=models.CASCADE,
        related_name='purchase_items',
        verbose_name='상품번호'
    )
    quantity = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='수량'
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
        db_table = 'purchase_items'
        verbose_name = 'Purchase Item'
        verbose_name_plural = 'Purchase Items'
        ordering = ['-created_at']

    def __str__(self):
        return f"Purchase {self.purchase_id} - Product {self.product_id} x {self.quantity}"

    @property
    def is_deleted(self) -> bool:
        """Check if purchase item is soft deleted."""
        return self.deleted_at is not None


class TokenHistoryModel(models.Model):
    """Token transaction history (토큰 결제 이력) model."""

    TRANSACTION_TYPE_CHOICES = [
        ('charge', '충전'),
        ('payment', '결제'),
    ]

    transaction_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name='유형',
        help_text='충전/결제'
    )
    token_change = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='변동된 토큰양',
        help_text='충전은+/결제는-'
    )
    token_balance_after = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='변동후토큰양'
    )
    token_owner_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='토큰 주인',
        help_text='결제 토큰 조회목적'
    )
    transaction_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='거래일시'
    )
    danawa_product_id = models.CharField(
        max_length=15,
        verbose_name='상품번호',
        help_text='다나와 상품 고유 번호(가격변동 값 API 사용시 필요)'
    )
    user = models.ForeignKey(
        'users.UserModel',
        on_delete=models.CASCADE,
        related_name='token_histories',
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
        db_table = 'token_histories'
        verbose_name = 'Token History'
        verbose_name_plural = 'Token Histories'
        ordering = ['-transaction_at']
        indexes = [
            models.Index(fields=['user', 'transaction_at']),
        ]

    def __str__(self):
        return f"{self.transaction_type}: {self.token_change} tokens"

    @property
    def is_deleted(self) -> bool:
        """Check if token history is soft deleted."""
        return self.deleted_at is not None


class ReviewModel(models.Model):
    """Product review (리뷰) model."""

    mall_name = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='리뷰 쇼핑몰명'
    )
    reviewer_name = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='리뷰 작성자'
    )
    content = models.TextField(
        null=True,
        blank=True,
        verbose_name='내용'
    )
    rating = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='평점'
    )
    review_images = models.JSONField(
        default=list,
        blank=True,
        verbose_name='리뷰 이미지 URL 목록'
    )
    ai_review_summary = models.JSONField(
        null=True,
        blank=True,
        verbose_name='AI 리뷰 요약'
    )
    external_review_count = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='외부 쇼핑몰 리뷰 총합'
    )
    product = models.ForeignKey(
        'products.ProductModel',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='상품번호'
    )
    user = models.ForeignKey(
        'users.UserModel',
        on_delete=models.CASCADE,
        related_name='reviews',
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
        db_table = 'reviews'
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"Review by {self.reviewer_name} - Rating: {self.rating}"

    @property
    def is_deleted(self) -> bool:
        """Check if review is soft deleted."""
        return self.deleted_at is not None
