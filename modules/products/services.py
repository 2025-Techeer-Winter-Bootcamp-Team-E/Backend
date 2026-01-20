"""
Products module service layer.
"""
from datetime import datetime
from typing import Optional, List
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from modules.timers.models import PriceHistoryModel
from .models import ProductModel, MallInformationModel
from .exceptions import (
    ProductNotFoundError,
)


class ProductService:
    """
    Product business logic service.
    """

    def get_product_by_id(self, product_id: int) -> Optional[ProductModel]:
        """Get product by ID."""
        try:
            return ProductModel.objects.get(id=product_id, deleted_at__isnull=True)
        except ProductModel.DoesNotExist:
            return None

    def get_product_by_danawa_id(self, danawa_product_id: str) -> Optional[ProductModel]:
        """Get product by Danawa product ID."""
        try:
            return ProductModel.objects.get(danawa_product_id=danawa_product_id, deleted_at__isnull=True)
        except ProductModel.DoesNotExist:
            return None

    def get_products_by_ids(self, product_ids: List[int]) -> List[ProductModel]:
        """Get multiple products by IDs."""
        return list(ProductModel.objects.filter(id__in=product_ids, deleted_at__isnull=True))

    def get_all_products(
        self,
        category_id: int = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[ProductModel]:
        """Get all active products."""
        queryset = ProductModel.objects.filter(deleted_at__isnull=True)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return list(queryset.order_by('-created_at')[offset:offset + limit])


    def search_by_embedding(
        self,
        embedding: List[float],
        limit: int = 10,
    ) -> List[ProductModel]:
        """Search products by semantic similarity using pgvector."""
        from pgvector.django import L2Distance

        return list(
            ProductModel.objects
            .filter(deleted_at__isnull=True, detail_spec_vector__isnull=False)
            .order_by(L2Distance('detail_spec_vector', embedding))[:limit]
        )

    def create_product(
        self,
        danawa_product_id: str,
        name: str,
        lowest_price: int,
        brand: str,
        detail_spec: dict = None,
        category_id: int = None,
        registration_month: str = None,
        product_status: str = None,
    ) -> ProductModel:
        """Create a new product."""
        product = ProductModel.objects.create(
            danawa_product_id=danawa_product_id,
            name=name,
            lowest_price=lowest_price,
            brand=brand,
            detail_spec=detail_spec or {},
            category_id=category_id,
            registration_month=registration_month,
            product_status=product_status,
        )
        return product

    def update_product(
        self,
        product_id: int,
        **kwargs
    ) -> ProductModel:
        """Update product information."""
        product = self.get_product_by_id(product_id)
        if not product:
            raise ProductNotFoundError(str(product_id))

        for key, value in kwargs.items():
            if hasattr(product, key) and value is not None:
                setattr(product, key, value)

        product.save()
        return product

    def delete_product(self, product_id: int) -> bool:
        """Soft delete a product."""
        product = self.get_product_by_id(product_id)
        if not product:
            return False

        product.deleted_at = datetime.now()
        product.save()
        return True
    
    def get_price_trend_data(self, product: ProductModel, months: int = 6): #views.py에서 탐색 기간 설정 조작가능
        start_date = timezone.now() - relativedelta(months=months)

        # 2. 필터 조건에 '날짜' 추가 (start_date 이후 데이터만!)
        histories = PriceHistoryModel.objects.filter(
            danawa_product_id=product.danawa_product_id,
            recorded_at__gte=start_date, # 탐색 기간 설정 로직
            deleted_at__isnull=True
        ).order_by('recorded_at')
        
        return {
            "product_id": product.id,
            "product_name": product.name,
            "period_unit": "month",
            "selected_period": months,
            "price_history": histories
        }

class MallInformationService:
    """
    Mall information business logic service.
    """

    def get_mall_info_by_product(self, product_id: int) -> List[MallInformationModel]:
        """Get all mall information for a product."""
        return list(
            MallInformationModel.objects.filter(
                product_id=product_id,
                deleted_at__isnull=True
            ).order_by('current_price')
        )

    def create_mall_info(
        self,
        product_id: int,
        mall_name: str,
        current_price: int,
        product_page_url: str = None,
        seller_logo_url: str = None,
        representative_image_url: str = None,
        additional_image_urls: list = None,
    ) -> MallInformationModel:
        """Create mall information."""
        return MallInformationModel.objects.create(
            product_id=product_id,
            mall_name=mall_name,
            current_price=current_price,
            product_page_url=product_page_url,
            seller_logo_url=seller_logo_url,
            representative_image_url=representative_image_url,
            additional_image_urls=additional_image_urls or [],
        )

    def update_mall_price(
        self,
        mall_info_id: int,
        current_price: int,
    ) -> MallInformationModel:
        """Update mall price."""
        try:
            mall_info = MallInformationModel.objects.get(
                id=mall_info_id,
                deleted_at__isnull=True
            )
            mall_info.current_price = current_price
            mall_info.save()
            return mall_info
        except MallInformationModel.DoesNotExist:
            return None
