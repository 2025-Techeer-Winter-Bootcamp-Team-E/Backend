"""
Search business logic services.
"""
import logging
from datetime import datetime
from typing import List, Optional

from .models import SearchModel, RecentViewProductModel

logger = logging.getLogger(__name__)


class SearchService:
    """Service for search operations."""

    def search_products(
        self,
        query: str,
        search_mode: str = 'basic',
        user_id: int = None,
        danawa_product_id: str = '',
    ) -> dict:
        """
        Search products.

        Args:
            query: Search query string
            search_mode: 'basic', 'llm', or 'shopping_research'
            user_id: User ID for history tracking
            danawa_product_id: Danawa product ID if applicable
        """
        from modules.products.services import ProductService
        product_service = ProductService()

        # Perform search
        results = product_service.search_products(query, limit=20)

        # Record search history if user is logged in
        if user_id:
            self.record_search(
                user_id=user_id,
                query=query,
                search_mode=search_mode,
                danawa_product_id=danawa_product_id,
            )

        return {
            'results': results,
            'total': len(results),
            'query': query,
            'search_mode': search_mode
        }

    def record_search(
        self,
        user_id: int,
        query: str,
        search_mode: str,
        danawa_product_id: str = '',
    ) -> SearchModel:
        """Record search in history."""
        return SearchModel.objects.create(
            user_id=user_id,
            query=query,
            search_mode=search_mode,
            searched_at=datetime.now(),
            danawa_product_id=danawa_product_id,
        )

    def get_user_search_history(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[SearchModel]:
        """Get user's recent search history."""
        return list(
            SearchModel.objects.filter(
                user_id=user_id,
                deleted_at__isnull=True
            ).order_by('-searched_at')[:limit]
        )


class RecentViewProductService:
    """Service for recent view product operations."""

    def record_view(
        self,
        user_id: int,
        danawa_product_id: str,
    ) -> RecentViewProductModel:
        """Record a product view."""
        recent_view, created = RecentViewProductModel.objects.get_or_create(
            user_id=user_id,
            danawa_product_id=danawa_product_id,
        )

        if not created:
            recent_view.save()  # Update updated_at

        return recent_view

    def get_user_recent_views(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[RecentViewProductModel]:
        """Get user's recently viewed products."""
        return list(
            RecentViewProductModel.objects.filter(
                user_id=user_id,
                deleted_at__isnull=True
            ).order_by('-updated_at')[:limit]
        )

    def delete_recent_view(
        self,
        user_id: int,
        danawa_product_id: str,
    ) -> bool:
        """Delete a recent view (soft delete)."""
        try:
            recent_view = RecentViewProductModel.objects.get(
                user_id=user_id,
                danawa_product_id=danawa_product_id,
                deleted_at__isnull=True
            )
            recent_view.deleted_at = datetime.now()
            recent_view.save()
            return True
        except RecentViewProductModel.DoesNotExist:
            return False
