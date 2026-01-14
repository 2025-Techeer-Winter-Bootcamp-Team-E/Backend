"""
Products API v1 views.
"""
from decimal import Decimal
from uuid import UUID

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ....domain.entities.product import Product
from ....domain.entities.category import Category
from ....application.dtos.product_dto import ProductDTO
from ....infrastructure.repositories import DjangoProductRepository, DjangoCategoryRepository
from ...serializers.product_serializer import (
    ProductSerializer,
    ProductCreateSerializer,
    ProductUpdateSerializer,
)
from ...serializers.category_serializer import (
    CategorySerializer,
    CategoryCreateSerializer,
)


@extend_schema(tags=['Products'])
class ProductListCreateView(APIView):
    """Product list and create endpoint."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='category_id', type=str, required=False),
            OpenApiParameter(name='limit', type=int, required=False),
            OpenApiParameter(name='offset', type=int, required=False),
        ],
        responses={200: ProductSerializer(many=True)},
        summary="List products",
    )
    def get(self, request):
        repository = DjangoProductRepository()

        category_id = request.query_params.get('category_id')
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))

        products = repository.find_all(
            category_id=UUID(category_id) if category_id else None,
            offset=offset,
            limit=limit,
        )

        dtos = [ProductDTO.from_entity(p) for p in products]
        serializer = ProductSerializer(dtos, many=True)
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
        product = Product.create(
            name=data['name'],
            description=data['description'],
            sku=data['sku'],
            price=Decimal(str(data['price'])),
            currency=data.get('currency', 'KRW'),
            stock_quantity=data['stock_quantity'],
            category_id=data['category_id'],
            images=data.get('images', []),
        )

        repository = DjangoProductRepository()
        saved = repository.save(product)

        output = ProductSerializer(ProductDTO.from_entity(saved))
        return Response(output.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Products'])
class ProductDetailView(APIView):
    """Product detail endpoint."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        responses={200: ProductSerializer},
        summary="Get product detail",
    )
    def get(self, request, product_id: UUID):
        repository = DjangoProductRepository()
        product = repository.find_by_id(product_id)
        if not product:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(ProductDTO.from_entity(product))
        return Response(serializer.data)

    @extend_schema(
        request=ProductUpdateSerializer,
        responses={200: ProductSerializer},
        summary="Update a product",
    )
    def patch(self, request, product_id: UUID):
        repository = DjangoProductRepository()
        product = repository.find_by_id(product_id)
        if not product:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        from ....domain.value_objects.money import Money
        data = serializer.validated_data

        price = None
        if 'price' in data:
            price = Money(amount=Decimal(str(data['price'])), currency=data.get('currency', product.price.currency))

        product.update_info(
            name=data.get('name'),
            description=data.get('description'),
            price=price,
        )

        saved = repository.save(product)
        output = ProductSerializer(ProductDTO.from_entity(saved))
        return Response(output.data)

    @extend_schema(summary="Delete a product")
    def delete(self, request, product_id: UUID):
        repository = DjangoProductRepository()
        deleted = repository.delete(product_id)
        if not deleted:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Products'])
class ProductSearchView(APIView):
    """Product search endpoint."""
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='q', type=str, required=True, description="Search query"),
            OpenApiParameter(name='category_id', type=str, required=False),
            OpenApiParameter(name='limit', type=int, required=False),
        ],
        responses={200: ProductSerializer(many=True)},
        summary="Search products",
    )
    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'Query parameter required'}, status=status.HTTP_400_BAD_REQUEST)

        repository = DjangoProductRepository()
        category_id = request.query_params.get('category_id')
        limit = int(request.query_params.get('limit', 20))

        products = repository.search(
            query=query,
            category_id=UUID(category_id) if category_id else None,
            limit=limit,
        )

        dtos = [ProductDTO.from_entity(p) for p in products]
        serializer = ProductSerializer(dtos, many=True)
        return Response(serializer.data)


@extend_schema(tags=['Categories'])
class CategoryListCreateView(APIView):
    """Category list and create endpoint."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        responses={200: CategorySerializer(many=True)},
        summary="List categories",
    )
    def get(self, request):
        repository = DjangoCategoryRepository()
        categories = repository.find_all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=CategoryCreateSerializer,
        responses={201: CategorySerializer},
        summary="Create a category",
    )
    def post(self, request):
        serializer = CategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        category = Category.create(
            name=data['name'],
            description=data.get('description', ''),
            parent_id=data.get('parent_id'),
        )

        repository = DjangoCategoryRepository()
        saved = repository.save(category)

        output = CategorySerializer(saved)
        return Response(output.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Categories'])
class CategoryDetailView(APIView):
    """Category detail endpoint."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        responses={200: CategorySerializer},
        summary="Get category detail",
    )
    def get(self, request, category_id: UUID):
        repository = DjangoCategoryRepository()
        category = repository.find_by_id(category_id)
        if not category:
            return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CategorySerializer(category)
        return Response(serializer.data)

    @extend_schema(summary="Delete a category")
    def delete(self, request, category_id: UUID):
        repository = DjangoCategoryRepository()
        deleted = repository.delete(category_id)
        if not deleted:
            return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
