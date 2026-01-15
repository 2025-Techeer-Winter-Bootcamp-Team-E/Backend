"""
Products module Celery tasks.
"""
from celery import shared_task
from django.conf import settings


@shared_task(name='modules.products.tasks.generate_product_embedding')
def generate_product_embedding(product_id: str):
    """Generate embedding for a product using OpenAI."""
    from .models import ProductModel

    try:
        product = ProductModel.objects.get(id=product_id)
    except ProductModel.DoesNotExist:
        return False

    # Combine name and description for embedding
    text = f"{product.name}. {product.description}"

    try:
        from shared.ai_clients import OpenAIClient
        client = OpenAIClient()
        embedding = client.create_embedding(text)

        product.embedding = embedding
        product.save()
        return True
    except Exception as e:
        print(f"Error generating embedding for product {product_id}: {e}")
        return False


@shared_task(name='modules.products.tasks.update_all_embeddings')
def update_all_embeddings():
    """Update embeddings for all products without embeddings."""
    from .models import ProductModel

    products = ProductModel.objects.filter(embedding__isnull=True, is_active=True)

    for product in products:
        generate_product_embedding.delay(str(product.id))

    return f"Queued {products.count()} products for embedding generation"


@shared_task(name='modules.products.tasks.sync_product_stock')
def sync_product_stock(product_id: str, quantity_change: int):
    """Sync product stock (for external integrations)."""
    from .models import ProductModel

    try:
        product = ProductModel.objects.get(id=product_id)
        product.stock_quantity += quantity_change
        if product.stock_quantity < 0:
            product.stock_quantity = 0
        product.save()
        return True
    except ProductModel.DoesNotExist:
        return False
