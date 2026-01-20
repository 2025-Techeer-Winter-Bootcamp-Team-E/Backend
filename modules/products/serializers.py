"""
Products module serializers.
"""
from rest_framework import serializers
from .models import ProductModel, MallInformationModel
from modules.timers.models import PriceHistoryModel

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
