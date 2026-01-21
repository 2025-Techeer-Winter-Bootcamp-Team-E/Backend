"""
Search serializers.
"""
from rest_framework import serializers

from .models import SearchModel, RecentViewProductModel


class SearchQuerySerializer(serializers.Serializer):
    """Serializer for search request."""

    query = serializers.CharField(
        min_length=2,
        max_length=500,
        help_text='Search query text'
    )
    search_mode = serializers.ChoiceField(
        choices=['basic', 'llm', 'shopping_research'],
        default='basic',
        help_text='Type of search to perform'
    )
    category_id = serializers.IntegerField(
        required=False,
        help_text='Filter by category'
    )
    page = serializers.IntegerField(
        min_value=1,
        default=1,
        help_text='Page number'
    )
    page_size = serializers.IntegerField(
        min_value=1,
        max_value=100,
        default=20,
        help_text='Results per page'
    )


class SearchResultSerializer(serializers.Serializer):
    """Serializer for search results."""

    results = serializers.ListField(
        help_text='List of product results'
    )
    total = serializers.IntegerField(
        help_text='Total number of results'
    )
    query = serializers.CharField()
    search_mode = serializers.CharField()


class SearchHistorySerializer(serializers.ModelSerializer):
    """Serializer for search history."""

    class Meta:
        model = SearchModel
        fields = [
            'id',
            'query',
            'search_mode',
            'searched_at',
            'danawa_product_id',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class RecentViewProductSerializer(serializers.ModelSerializer):
    """Serializer for recent view products."""

    class Meta:
        model = RecentViewProductModel
        fields = [
            'id',
            'danawa_product_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecentViewProductCreateSerializer(serializers.Serializer):
    """Serializer for creating recent view product."""

    danawa_product_id = serializers.CharField(max_length=15)

class AutocompleteResponseSerializer(serializers.Serializer):
    """자동완성 응답을 위한 시리얼라이저"""
    suggestions = serializers.ListField(
        child=serializers.CharField(),
        help_text='추천 검색어 리스트'
    )
class AutocompleteBaseResponseSerializer(serializers.Serializer):
    """명세서 규격에 맞춘 최종 응답 시리얼라이저"""
    status = serializers.IntegerField(default=200)
    message = serializers.CharField(default="자동완성 목록 조회 성공")
    data = AutocompleteResponseSerializer()


class PopularTermSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    term = serializers.CharField()

class PopularTermsResponseSerializer(serializers.Serializer):
    status = serializers.IntegerField(default=200)
    message = serializers.CharField(default="검색어 목록 조회 성공")
    data = serializers.DictField(
        child=serializers.ListField(child=PopularTermSerializer())
    )

class RecentSearchSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    term = serializers.CharField(source='query')  # query 필드를 term으로 매핑
    searchedAt = serializers.DateTimeField(source='searched_at')  # searched_at을 searchedAt으로 매핑

class RecentSearchResponseSerializer(serializers.Serializer):
    status = serializers.IntegerField(default=200)
    message = serializers.CharField(default="검색어 목록 조회 성공")
    data = serializers.DictField() # {"recent_terms": [...]} 형태


# LLM 기반 상품 추천 검색 시리얼라이저
class LLMRecommendationRequestSerializer(serializers.Serializer):
    """LLM 추천 검색 요청 시리얼라이저"""
    user_query = serializers.CharField(
        min_length=5,
        max_length=500,
        help_text='자연어로 된 사용자 검색 쿼리 (예: "전공 서적 많이 들고 다니는 컴공생인데...")'
    )


class ProductSpecSerializer(serializers.Serializer):
    """상품 스펙 시리얼라이저"""
    cpu = serializers.CharField(allow_null=True, help_text='CPU 정보')
    ram = serializers.CharField(allow_null=True, help_text='RAM 용량')
    storage = serializers.CharField(allow_null=True, help_text='저장장치 용량')
    display = serializers.CharField(allow_null=True, help_text='디스플레이 크기')
    weight = serializers.CharField(allow_null=True, help_text='무게')
    gpu = serializers.CharField(allow_null=True, help_text='GPU 정보')
    battery = serializers.CharField(allow_null=True, help_text='배터리 용량')


class RecommendedProductSerializer(serializers.Serializer):
    """추천 상품 시리얼라이저"""
    product_code = serializers.CharField(help_text='다나와 상품 고유 코드')
    name = serializers.CharField(help_text='상품명')
    brand = serializers.CharField(help_text='브랜드/제조사')
    price = serializers.IntegerField(help_text='최저가')
    thumbnail_url = serializers.CharField(allow_null=True, help_text='썸네일 이미지 URL')
    product_detail_url = serializers.CharField(allow_null=True, help_text='상품 상세 페이지 URL')
    recommendation_reason = serializers.CharField(help_text='AI 추천 사유')
    specs = ProductSpecSerializer(help_text='주요 스펙 정보')
    review_count = serializers.IntegerField(help_text='리뷰 수')
    review_rating = serializers.FloatField(allow_null=True, help_text='평균 별점')


class LLMRecommendationDataSerializer(serializers.Serializer):
    """LLM 추천 응답 데이터 시리얼라이저"""
    analysis_message = serializers.CharField(help_text='AI 분석 메시지')
    recommended_products = RecommendedProductSerializer(many=True, help_text='추천 상품 목록 (5개)')


class LLMRecommendationResponseSerializer(serializers.Serializer):
    """LLM 추천 검색 응답 시리얼라이저"""
    status = serializers.IntegerField(default=200, help_text='응답 상태 코드')
    message = serializers.CharField(default="추천 검색 성공", help_text='응답 메시지')
    data = LLMRecommendationDataSerializer(help_text='추천 결과 데이터')