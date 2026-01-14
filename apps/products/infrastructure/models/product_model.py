"""
Product Django ORM model.
"""
import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from pgvector.django import VectorField


class ProductModel(models.Model):
    """Product model with pgvector support."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField()
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KRW')
    stock_quantity = models.PositiveIntegerField(default=0)
    category_id = models.UUIDField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    # pgvector embedding field (OpenAI ada-002: 1536 dimensions)
    embedding = VectorField(dimensions=1536, null=True, blank=True)

    # Product images
    images = ArrayField(
        models.URLField(max_length=500),
        default=list,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category_id', 'is_active']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"
