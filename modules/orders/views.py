"""
Orders module API views.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import StorageService, PurchaseService, TokenHistoryService, ReviewService
from .serializers import (
    StorageItemSerializer,
    StorageItemCreateSerializer,
    StorageItemUpdateSerializer,
    PurchaseSerializer,
    TokenHistorySerializer,
    ReviewSerializer,
    ReviewCreateSerializer,
)


storage_service = StorageService()
purchase_service = PurchaseService()
token_history_service = TokenHistoryService()
review_service = ReviewService()


@extend_schema(tags=['Storage'])
class StorageListView(APIView):
    """Storage (장바구니) list endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: StorageItemSerializer(many=True)},
        summary="Get current user's storage items",
    )
    def get(self, request):
        items = storage_service.get_user_storage_items(request.user.id)
        return Response(StorageItemSerializer(items, many=True).data)

    @extend_schema(
        request=StorageItemCreateSerializer,
        responses={201: StorageItemSerializer},
        summary="Add item to storage",
    )
    def post(self, request):
        serializer = StorageItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        item = storage_service.add_item(
            user_id=request.user.id,
            product_id=data['product_id'],
            quantity=data['quantity'],
        )

        return Response(StorageItemSerializer(item).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Storage'])
class StorageItemView(APIView):
    """Storage item endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=StorageItemUpdateSerializer,
        responses={200: StorageItemSerializer},
        summary="Update storage item quantity",
    )
    def patch(self, request, product_id: int):
        serializer = StorageItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item = storage_service.update_item_quantity(
            user_id=request.user.id,
            product_id=product_id,
            quantity=serializer.validated_data['quantity'],
        )

        if item:
            return Response(StorageItemSerializer(item).data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="Remove item from storage")
    def delete(self, request, product_id: int):
        storage_service.remove_item(request.user.id, product_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Purchase'])
class PurchaseListCreateView(APIView):
    """Purchase list and create endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: PurchaseSerializer(many=True)},
        summary="List user's purchases",
    )
    def get(self, request):
        purchases = purchase_service.get_user_purchases(request.user.id)
        return Response(PurchaseSerializer(purchases, many=True).data)

    @extend_schema(
        responses={201: PurchaseSerializer},
        summary="Create purchase from storage",
    )
    def post(self, request):
        purchase = purchase_service.create_purchase_from_storage(request.user.id)
        return Response(PurchaseSerializer(purchase).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Purchase'])
class PurchaseDetailView(APIView):
    """Purchase detail endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: PurchaseSerializer},
        summary="Get purchase detail",
    )
    def get(self, request, purchase_id: int):
        purchase = purchase_service.get_purchase_by_id(purchase_id)
        if not purchase:
            return Response({'error': 'Purchase not found'}, status=status.HTTP_404_NOT_FOUND)

        if purchase.user_id != request.user.id:
            return Response({'error': 'Purchase not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response(PurchaseSerializer(purchase).data)


@extend_schema(tags=['Token'])
class TokenHistoryListView(APIView):
    """Token history list endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: TokenHistorySerializer(many=True)},
        summary="List user's token histories",
    )
    def get(self, request):
        histories = token_history_service.get_user_token_histories(request.user.id)
        return Response(TokenHistorySerializer(histories, many=True).data)


@extend_schema(tags=['Review'])
class ReviewListCreateView(APIView):
    """Review list and create endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: ReviewSerializer(many=True)},
        summary="List user's reviews",
    )
    def get(self, request):
        reviews = review_service.get_user_reviews(request.user.id)
        return Response(ReviewSerializer(reviews, many=True).data)

    @extend_schema(
        request=ReviewCreateSerializer,
        responses={201: ReviewSerializer},
        summary="Create a review",
    )
    def post(self, request):
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        review = review_service.create_review(
            product_id=data['product_id'],
            user_id=request.user.id,
            content=data.get('content'),
            rating=data.get('rating'),
            mall_name=data.get('mall_name'),
            reviewer_name=data.get('reviewer_name'),
        )

        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Review'])
class ProductReviewListView(APIView):
    """Product review list endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: ReviewSerializer(many=True)},
        summary="List product reviews",
    )
    def get(self, request, product_id: int):
        reviews = review_service.get_product_reviews(product_id)
        return Response(ReviewSerializer(reviews, many=True).data)
