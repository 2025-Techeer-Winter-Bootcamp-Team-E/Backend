"""
Products module API views.
"""
from drf_spectacular.utils import extend_schema,OpenApiResponse,OpenApiParameter
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import ProductService, MallInformationService,ProductService
from .serializers import (
    ProductSerializer,
    ProductListSerializer,
    ProductCreateSerializer,
    ProductUpdateSerializer,
    ProductPriceTrendSerializer,
    MallInformationSerializer,
    MallInformationCreateSerializer,
)


product_service = ProductService()
mall_info_service = MallInformationService()


@extend_schema(tags=['Products'])
class ProductListCreateView(APIView):
    """Product list and create endpoint."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='category_id', type=int, required=False),
            OpenApiParameter(name='limit', type=int, required=False),
            OpenApiParameter(name='offset', type=int, required=False),
        ],
        responses={200: ProductListSerializer(many=True)},
        summary="List products",
    )
    def get(self, request):
        category_id = request.query_params.get('category_id')
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))

        products = product_service.get_all_products(
            category_id=int(category_id) if category_id else None,
            offset=offset,
            limit=limit,
        )

        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=ProductCreateSerializer,
        responses={201: ProductSerializer},
        summary="Create a product",
    )
    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        product = product_service.create_product(
            danawa_product_id=data['danawa_product_id'],
            name=data['name'],
            lowest_price=data['lowest_price'],
            brand=data['brand'],
            detail_spec=data.get('detail_spec', {}),
            category_id=data.get('category_id'),
            registration_month=data.get('registration_month'),
            product_status=data.get('product_status'),
        )

        output = ProductSerializer(product)
        return Response(output.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Products'])
class ProductDetailView(APIView):
    """Product detail endpoint."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    @extend_schema(
        responses={200: ProductSerializer},
        summary="Get product detail",
    )
    def get(self, request, product_id: int):
        product = product_service.get_product_by_id(product_id)
        if not product:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(product)
        return Response(serializer.data)

    @extend_schema(
        request=ProductUpdateSerializer,
        responses={200: ProductSerializer},
        summary="Update a product",
    )
    def patch(self, request, product_id: int):
        serializer = ProductUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        product = product_service.update_product(
            product_id=product_id,
            **serializer.validated_data
        )

        output = ProductSerializer(product)
        return Response(output.data)

    @extend_schema(summary="Delete a product")
    def delete(self, request, product_id: int):
        deleted = product_service.delete_product(product_id)
        if not deleted:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Products'])
class ProductMallInfoView(APIView):
    """Product mall information endpoint."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAdminUser()]

    @extend_schema(
        responses={200: MallInformationSerializer(many=True)},
        summary="Get mall information for a product",
    )
    def get(self, request, product_id: int):
        mall_info = mall_info_service.get_mall_info_by_product(product_id)
        serializer = MallInformationSerializer(mall_info, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=MallInformationCreateSerializer,
        responses={201: MallInformationSerializer},
        summary="Add mall information to a product",
    )
    def post(self, request, product_id: int):
        serializer = MallInformationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        mall_info = mall_info_service.create_mall_info(
            product_id=product_id,
            mall_name=data['mall_name'],
            current_price=data['current_price'],
            product_page_url=data.get('product_page_url'),
            seller_logo_url=data.get('seller_logo_url'),
            representative_image_url=data.get('representative_image_url'),
            additional_image_urls=data.get('additional_image_urls', []),
        )

        output = MallInformationSerializer(mall_info)
        return Response(output.data, status=status.HTTP_201_CREATED)

@extend_schema(tags=['Products'])
class ProductPriceTrendView(APIView):
    """상품의 월별 최저가 추이를 조회하는 API입니다."""
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get product price trend",
        responses={
            200: ProductPriceTrendSerializer,
            400: OpenApiResponse(description="지원하지 않는 조회 기간입니다. (6, 12, 24 중 선택 가능)"), #
            404: OpenApiResponse(description="상품 가격 이력 데이터를 찾을 수 없습니다.") #
        }
    )
    def get(self, request, product_id: int):
        # 1. 조회 기간(months) 검증 (명세서 400 에러 대응)
        try:
            months = int(request.query_params.get('months', 6))
        except ValueError:
            months = 0 # 숫자가 아니면 아래 조건에서 걸러지게 함

        if months not in [6, 12, 24]:
            return Response({
                "status": 400,
                "message": "지원하지 않는 조회 기간입니다. (6, 12, 24 중 선택 가능)"
            }, status=status.HTTP_400_BAD_REQUEST) #

        # 2. 상품 존재 여부 확인
        product = product_service.get_product_by_id(product_id)
        if not product:
            return Response({
                "status": 404,
                "message": "상품 가격 이력 데이터를 찾을 수 없습니다."
            }, status=status.HTTP_404_NOT_FOUND) #

        # 3. 데이터 조회 및 응답
        trend_data = product_service.get_price_trend_data(product, months=months)
        serializer = ProductPriceTrendSerializer(trend_data)
        
        # 성공 시 응답 구조도 status를 포함하고 싶다면 아래처럼 보낼 수 있습니다.
        return Response({
            "status": 200,
            "data": serializer.data
        })