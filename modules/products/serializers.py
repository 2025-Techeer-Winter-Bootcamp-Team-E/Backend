"""
Products module serializers.
"""
from rest_framework import serializers
from .models import ProductModel, MallInformationModel
from modules.timers.models import PriceHistoryModel
from modules.orders.models import ReviewModel
class MallInformationSerializer(serializers.ModelSerializer):
    """Serializer for mall information."""

    class Meta:
        model = MallInformationModel
        fields = [
            'id',
            'mall_name',
            'current_price',
            'product_page_url',
            'seller_logo_url',
            'representative_image_url',
            'additional_image_urls',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for product output."""
    product_code = serializers.CharField(source='danawa_product_id', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    mall_information = MallInformationSerializer(many=True, read_only=True)

    class Meta:
        model = ProductModel
        fields = [
            'id',
            #'danawa_product_id', 'product_code'로 대체
            'product_code',
            'name',
            'lowest_price',
            'brand',
            'detail_spec',
            'registration_month',
            'product_status',
            'category',
            'category_name',
            'mall_information',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductListSerializer(serializers.ModelSerializer):
    """Simplified serializer for product list."""

    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)

    class Meta:
        model = ProductModel
        fields = [
            'id',
            'danawa_product_id',
            'name',
            'lowest_price', 
            'brand',
            'product_status',
            'category',
            'category_name',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

class ProductCreateSerializer(serializers.Serializer):
    """Serializer for product creation."""

    danawa_product_id = serializers.CharField(max_length=15)
    name = serializers.CharField(max_length=200)
    lowest_price = serializers.IntegerField(min_value=0)
    brand = serializers.CharField(max_length=50)
    detail_spec = serializers.JSONField(required=False, default=dict)
    registration_month = serializers.CharField(max_length=20, required=False, allow_blank=True)
    product_status = serializers.CharField(max_length=20, required=False, allow_blank=True)
    category_id = serializers.IntegerField(required=False, allow_null=True)


class ProductUpdateSerializer(serializers.Serializer):
    """Serializer for product update."""

    name = serializers.CharField(max_length=200, required=False)
    lowest_price = serializers.IntegerField(min_value=0, required=False)
    brand = serializers.CharField(max_length=50, required=False)
    detail_spec = serializers.JSONField(required=False)
    registration_month = serializers.CharField(max_length=20, required=False, allow_blank=True)
    product_status = serializers.CharField(max_length=20, required=False, allow_blank=True)
    category_id = serializers.IntegerField(required=False, allow_null=True)

#
class MallInformationCreateSerializer(serializers.Serializer):
    """Serializer for creating mall information."""

    mall_name = serializers.CharField(max_length=50)
    current_price = serializers.IntegerField(min_value=0)
    product_page_url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    seller_logo_url = serializers.CharField(max_length=300, required=False, allow_blank=True)
    representative_image_url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    additional_image_urls = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )

#과거 가격 시리얼 라이저(일 단위)
class PriceHistorySerializer(serializers.ModelSerializer):
    data =serializers.DateTimeField(source='recorded_at', format='%Y-%m-%d')
    price =serializers.IntegerField(source='lowest_price')

    class Meta:
        model=PriceHistoryModel
        fields=['data','price']


#가격 추이 시리얼 라이저(기간)       
class ProductPriceTrendSerializer(serializers.Serializer):
    product_code = serializers.IntegerField()
    product_name = serializers.CharField()
    period_unit = serializers.CharField(default="month")
    selected_period = serializers.IntegerField()
    price_history = PriceHistorySerializer(many=True)

class ReviewDetailSerializer(serializers.ModelSerializer):
    review_id = serializers.IntegerField(source='id') # 모델의 PK 
    author_name = serializers.CharField(source='reviewer_name')
    
    class Meta:
        model = ReviewModel
        fields = [
            'review_id', 
            'review_images', 
            'author_name', 
            'rating', 
            'content', 
            'created_at'
        ]

class ReviewListResponseSerializer(serializers.Serializer):
    pagination = serializers.DictField(child=serializers.IntegerField())#리뷰 페이지 정보
    average_rating = serializers.FloatField()     # 상품 전체 평점
    reviews = ReviewDetailSerializer(many=True)    # 아까 만든 리뷰 개별 데이터 리스트
    has_next = serializers.BooleanField()


# ===== 카테고리별 상품 목록 조회 API용 Serializers =====

class MallPriceSerializer(serializers.Serializer):
    """판매처별 가격 정보 Serializer (mall_price 배열용)"""
    mall_name = serializers.CharField()
    price = serializers.IntegerField(source='current_price')
    url = serializers.CharField(source='product_page_url', allow_null=True)


class ProductListItemSerializer(serializers.ModelSerializer):
    """상품 목록 아이템 Serializer (API 명세서 규격)"""
    product_code = serializers.CharField(source='danawa_product_id')
    product_name = serializers.CharField(source='name')
    specs = serializers.JSONField(source='detail_spec')
    base_price = serializers.IntegerField(source='lowest_price')
    category = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    mall_price = serializers.SerializerMethodField()

    class Meta:
        model = ProductModel
        fields = [
            'product_code',
            'product_name',
            'brand',
            'specs',
            'base_price',
            'category',
            'thumbnail_url',
            'mall_price',
        ]

    def get_category(self, obj):
        """카테고리 이름 반환"""
        return obj.category.name if obj.category else None

    def get_thumbnail_url(self, obj):
        """첫 번째 판매처의 대표 이미지 URL 반환"""
        mall_info = obj.mall_information.filter(deleted_at__isnull=True).first()
        return mall_info.representative_image_url if mall_info else None

    def get_mall_price(self, obj):
        """판매처별 가격 정보 리스트 반환"""
        mall_infos = obj.mall_information.filter(deleted_at__isnull=True)[:5]
        return MallPriceSerializer(mall_infos, many=True).data


class PaginationResponseSerializer(serializers.Serializer):
    """페이지네이션 정보 Serializer"""
    current_page = serializers.IntegerField()
    size = serializers.IntegerField()
    count = serializers.IntegerField()
    total_pages = serializers.IntegerField()


class ProductListDataSerializer(serializers.Serializer):
    """상품 목록 응답 Data Serializer"""
    pagination = PaginationResponseSerializer()
    products = ProductListItemSerializer(many=True)


class ProductSearchResponseSerializer(serializers.Serializer):
    """상품 목록 조회 최종 응답 Serializer"""
    status = serializers.IntegerField()
    data = ProductListDataSerializer()