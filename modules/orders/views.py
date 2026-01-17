"""
Orders module API views.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import CartService, OrderService, OrderHistoryService, ReviewService
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    CartItemCreateSerializer,
    CartItemUpdateSerializer,
    OrderSerializer,
    OrderHistorySerializer,
    ReviewSerializer,
    ReviewCreateSerializer,
)


cart_service = CartService()
order_service = OrderService()
order_history_service = OrderHistoryService()
review_service = ReviewService()


@extend_schema(tags=['Cart'])
class CartView(APIView):
    """Cart (장바구니) endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: CartSerializer},
        summary="Get current user's cart",
    )
    def get(self, request):
        cart = cart_service.get_or_create_cart(request.user.id)
        items = cart_service.get_cart_items(cart.id)
        cart.items = items  # Attach items for serializer
        return Response(CartSerializer(cart).data)


@extend_schema(tags=['Cart'])
class CartItemListCreateView(APIView):
    """Cart item list and create endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: CartItemSerializer(many=True)},
        summary="Get current user's cart items",
    )
    def get(self, request):
        cart = cart_service.get_or_create_cart(request.user.id)
        items = cart_service.get_cart_items(cart.id)
        return Response(CartItemSerializer(items, many=True).data)

    @extend_schema(
        request=CartItemCreateSerializer,
        responses={201: CartItemSerializer},
        summary="Add item to cart",
    )
    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        cart = cart_service.get_or_create_cart(request.user.id)
        item = cart_service.add_item(
            cart_id=cart.id,
            product_id=data['product_id'],
            quantity=data['quantity'],
        )

        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Cart'])
class CartItemDetailView(APIView):
    """Cart item detail endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CartItemUpdateSerializer,
        responses={200: CartItemSerializer},
        summary="Update cart item quantity",
    )
    def patch(self, request, product_id: int):
        serializer = CartItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = cart_service.get_or_create_cart(request.user.id)
        item = cart_service.update_item_quantity(
            cart_id=cart.id,
            product_id=product_id,
            quantity=serializer.validated_data['quantity'],
        )

        if item:
            return Response(CartItemSerializer(item).data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(summary="Remove item from cart")
    def delete(self, request, product_id: int):
        cart = cart_service.get_or_create_cart(request.user.id)
        cart_service.remove_item(cart.id, product_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Order'])
class OrderListCreateView(APIView):
    """Order list and create endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OrderSerializer(many=True)},
        summary="List user's orders",
    )
    def get(self, request):
        orders = order_service.get_user_orders(request.user.id)
        return Response(OrderSerializer(orders, many=True).data)

    @extend_schema(
        responses={201: OrderSerializer},
        summary="Create order from cart",
    )
    def post(self, request):
        order = order_service.create_order_from_cart(request.user.id)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Order'])
class OrderDetailView(APIView):
    """Order detail endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OrderSerializer},
        summary="Get order detail",
    )
    def get(self, request, order_id: int):
        order = order_service.get_order_by_id(order_id)
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        if order.user_id != request.user.id:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response(OrderSerializer(order).data)


@extend_schema(tags=['Order History'])
class OrderHistoryListView(APIView):
    """Order history list endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OrderHistorySerializer(many=True)},
        summary="List user's order histories",
    )
    def get(self, request):
        histories = order_history_service.get_user_order_histories(request.user.id)
        return Response(OrderHistorySerializer(histories, many=True).data)


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
            danawa_product_id=data['danawa_product_id'],
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
    def get(self, request, danawa_product_id: str):
        reviews = review_service.get_product_reviews(danawa_product_id)
        return Response(ReviewSerializer(reviews, many=True).data)
