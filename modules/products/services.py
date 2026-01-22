"""
Products module service layer.
"""
from datetime import datetime
from typing import Optional, List
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.db import models
from django.db.models import Q, Avg, Count
from modules.timers.models import PriceHistoryModel
from modules.orders.models import ReviewModel
from .models import ProductModel, MallInformationModel
from .exceptions import (
    ProductNotFoundError,
)
import math


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
    #이용자 서비스 용 get(product_code기반 호출)
    def get_product_by_code(self, product_code: str) -> Optional[ProductModel]:
        """Get product by Danawa product ID."""
        try:
            return ProductModel.objects.get(danawa_product_id=product_code, deleted_at__isnull=True)
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

    def search_products(
        self,
        query: str,
        category_id: int = None,
        limit: int = 20,
    ) -> List[ProductModel]:
        """
        Search products by name, brand, or specifications.

        Args:
            query: Search query string
            category_id: Optional category filter
            limit: Maximum number of results

        Returns:
            List of matching ProductModel instances
        """
        if not query or len(query.strip()) < 1:
            return []

        query = query.strip()

        # Build search filter using Q objects
        search_filter = Q(deleted_at__isnull=True) & (
            Q(name__icontains=query) |
            Q(brand__icontains=query)
        )

        # Add category filter if provided
        if category_id:
            search_filter &= Q(category_id=category_id)

        # Execute search query
        results = ProductModel.objects.filter(search_filter).order_by(
            '-review_count',  # Popular products first
            '-created_at'
        )[:limit]

        return list(results)

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

    def get_products_with_filters(
        self,
        query: str = None,
        main_cat: str = None,
        sub_cat: str = None,
        brand: str = None,
        min_price: int = None,
        max_price: int = None,
        sort: str = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        """
        다중 조건 필터링 및 검색 기능이 포함된 상품 목록 조회.

        Args:
            query: 검색어 (상품명, 브랜드)
            main_cat: 대분류 카테고리 이름
            sub_cat: 중분류 카테고리 이름
            brand: 브랜드/제조사
            min_price: 최소 가격
            max_price: 최대 가격
            sort: 정렬 (price_low, price_high, popular)
            page: 페이지 번호
            page_size: 페이지 크기

        Returns:
            dict: {
                'products': List[ProductModel],
                'total_count': int,
                'page': int,
                'page_size': int,
                'total_pages': int
            }
        """
        from modules.categories.models import CategoryModel
        from django.db.models import Prefetch

        queryset = ProductModel.objects.filter(deleted_at__isnull=True)

        # 1. 검색어 필터 (q)
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(brand__icontains=query)
            )

        # 2. 대분류 필터 (main_cat) - level=0
        if main_cat:
            main_category = CategoryModel.objects.filter(
                name__icontains=main_cat,
                level=0,
                deleted_at__isnull=True
            ).first()
            if main_category:
                category_ids = self._get_descendant_category_ids(main_category.id)
                queryset = queryset.filter(category_id__in=category_ids)

        # 3. 중분류 필터 (sub_cat) - level=1
        if sub_cat:
            sub_category = CategoryModel.objects.filter(
                name__icontains=sub_cat,
                level=1,
                deleted_at__isnull=True
            ).first()
            if sub_category:
                category_ids = self._get_descendant_category_ids(sub_category.id)
                queryset = queryset.filter(category_id__in=category_ids)

        # 4. 브랜드 필터 (brand)
        if brand:
            queryset = queryset.filter(brand__icontains=brand)

        # 5. 가격 범위 필터 (min_price, max_price)
        if min_price is not None:
            queryset = queryset.filter(lowest_price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(lowest_price__lte=max_price)

        # 6. 정렬 (sort)
        if sort == 'price_low':
            queryset = queryset.order_by('lowest_price')
        elif sort == 'price_high':
            queryset = queryset.order_by('-lowest_price')
        elif sort == 'popular':
            queryset = queryset.order_by('-review_count', '-review_rating')
        else:
            queryset = queryset.order_by('-created_at')

        # 7. 전체 개수 계산
        total_count = queryset.count()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

        # 8. N+1 쿼리 방지를 위한 prefetch
        queryset = queryset.select_related('category').prefetch_related(
            Prefetch(
                'mall_information',
                queryset=MallInformationModel.objects.filter(deleted_at__isnull=True)
            )
        )

        # 9. 페이지네이션 적용
        offset = (page - 1) * page_size
        products = list(queryset[offset:offset + page_size])

        return {
            'products': products,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }

    def _get_descendant_category_ids(self, category_id: int) -> list:
        """
        특정 카테고리의 모든 하위 카테고리 ID를 재귀적으로 수집.

        Args:
            category_id: 시작 카테고리 ID

        Returns:
            list: 해당 카테고리 및 모든 하위 카테고리 ID 목록
        """
        from modules.categories.models import CategoryModel

        ids = [category_id]
        children = CategoryModel.objects.filter(
            parent_id=category_id,
            deleted_at__isnull=True
        )
        for child in children:
            ids.extend(self._get_descendant_category_ids(child.id))
        return ids

    def get_price_trend_data(self, product: ProductModel, months: int = 6): #views.py에서 탐색 기간 설정 조작가능
        start_date = timezone.now() - relativedelta(months=months)

        # 2. 필터 조건에 '날짜' 추가 (start_date 이후 데이터만!)
        histories = PriceHistoryModel.objects.filter(
            danawa_product_id=product.danawa_product_id,
            recorded_at__gte=start_date, # 탐색 기간 설정 로직
            deleted_at__isnull=True
        ).order_by('recorded_at')
        
        return {
            "product_code": product.danawa_product_id,
            "product_name": product.name,
            "period_unit": "month",
            "selected_period": months,
            "price_history": histories
        }
    def get_product_reviews(product_code, page=1, size=5):

        if not ProductModel.objects.filter(danawa_product_id=product_code).exists():
            return None
        
        queryset = ReviewModel.objects.filter(
            danawa_product_id=product_code,
            deleted_at__isnull=True
        )
    
        stats = queryset.aggregate(
            total_elements=models.Count('id'),
            average_rating=Avg('rating')
        )
        
        total_elements = stats['total_elements'] or 0
        average_rating = round(stats['average_rating'] or 0.0, 1) #평점 없을 경우 0점
        start = (page - 1) * size
        end = start + size
        reviews = queryset.all()[start:end] 

        total_pages = math.ceil(total_elements / size) if total_elements > 0 else 0
        has_next = page < total_pages
        
        return {
            "pagination": {
                "current_page": page,
                "size": size,
                "total_elements": total_elements,
                "total_pages": total_pages
            },
            "average_rating": average_rating,
            "reviews": reviews,
            "has_next": has_next 
        }

class MallInformationService:
    """
    Mall information business logic service.
    """
    def get_mall_info_by_code(self, product_code: str) -> List[MallInformationModel]:
        """제품 코드(danawa_product_id)를 사용하여 판매처 정보를 조회합니다."""
        return list(
            MallInformationModel.objects.filter(
                product__danawa_product_id=product_code, # PK가 아닌 코드로 필터링
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

