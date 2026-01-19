"""
Products module Django ORM models based on ERD.
"""
from django.db import models
from pgvector.django import VectorField


class ProductModel(models.Model):
    """Product model with pgvector support."""

    danawa_product_id = models.CharField(
        max_length=15,
        unique=True,
        db_index=True,
        verbose_name='상품 고유 번호',
        help_text='다나와 상품 고유 번호(가격변동 값 API 사용시 필요)'
    )
    lowest_price = models.IntegerField(
        verbose_name='최저가'
    )
    name = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='상품명'
    )
    detail_spec = models.JSONField(
        default=dict,
        verbose_name='상세 스펙'
    )
    detail_spec_vector = VectorField(
        dimensions=1536,
        null=True,
        blank=True,
        verbose_name='상세 스펙 벡터'
    )
    brand = models.CharField(
        max_length=50,
        verbose_name='제조사/브랜드'
    )
    registration_month = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='등록월'
    )
    product_status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='상품상태'
    )
    review_count = models.IntegerField(
        default=0,
        verbose_name='리뷰 수'
    )
    review_rating = models.FloatField(
        null=True,
        blank=True,
        verbose_name='평균 별점'
    )
    category = models.ForeignKey(
        'categories.CategoryModel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='카테고리번호'
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
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['name']),
            models.Index(fields=['brand']),
        ]

    def __str__(self):
        return f"{self.name} ({self.danawa_product_id})"

    @property
    def is_deleted(self) -> bool:
        """Check if product is soft deleted."""
        return self.deleted_at is not None


class MallInformationModel(models.Model):
    """Mall-specific product price information."""

    current_price = models.IntegerField(
        verbose_name='현재가'
    )
    mall_name = models.CharField(
        max_length=50,
        verbose_name='판매처명'
    )
    product_page_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='판매페이지 URL'
    )
    seller_logo_url = models.CharField(
        max_length=300,
        null=True,
        blank=True,
        verbose_name='판매자 로고'
    )
    product_description_image_url = models.TextField(
        null=True,
        blank=True,
        verbose_name='제품설명이미지 URL'
    )
    detail_page_image_url = models.TextField(
        null=True,
        blank=True,
        verbose_name='상세페이지 이미지 URL'
    )
    additional_image_urls = models.JSONField(
        default=list,
        blank=True,
        verbose_name='추가이미지 URL 목록'
    )
    representative_image_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='대표이미지URL'
    )
    product = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name='mall_information',
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
        db_table = 'mall_information'
        verbose_name = 'Mall Information'
        verbose_name_plural = 'Mall Information'
        ordering = ['current_price']
        indexes = [
            models.Index(fields=['product', 'mall_name']),
        ]

    def __str__(self):
        return f"{self.mall_name}: {self.current_price}원"

    @property
    def is_deleted(self) -> bool:
        """Check if mall information is soft deleted."""
        return self.deleted_at is not None
