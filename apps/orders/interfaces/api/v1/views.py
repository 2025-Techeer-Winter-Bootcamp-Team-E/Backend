"""
Orders API v1 views.
"""
from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ...serializers.cart_serializer import CartSerializer, CartItemCreateSerializer
from ...serializers.order_serializer import OrderSerializer


@extend_schema(tags=['Cart'])
class CartView(APIView):
    """Cart endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: CartSerializer},
        summary="Get current user's cart",
    )
    def get(self, request):
        # TODO: Implement cart retrieval
        return Response({'items': [], 'total_amount': 0, 'item_count': 0})

    @extend_schema(
        request=CartItemCreateSerializer,
        responses={200: CartSerializer},
        summary="Add item to cart",
    )
    def post(self, request):
        # TODO: Implement add to cart
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'message': 'Item added to cart'})

    @extend_schema(summary="Clear cart")
    def delete(self, request):
        # TODO: Implement clear cart
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Cart'])
class CartItemView(APIView):
    """Cart item endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Update cart item quantity")
    def patch(self, request, product_id: UUID):
        # TODO: Implement update quantity
        return Response({'message': 'Item updated'})

    @extend_schema(summary="Remove item from cart")
    def delete(self, request, product_id: UUID):
        # TODO: Implement remove from cart
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Orders'])
class OrderListCreateView(APIView):
    """Order list and create endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OrderSerializer(many=True)},
        summary="List user's orders",
    )
    def get(self, request):
        # TODO: Implement order list
        return Response([])

    @extend_schema(
        responses={201: OrderSerializer},
        summary="Create order from cart",
    )
    def post(self, request):
        # TODO: Implement order creation
        return Response({'message': 'Order created'}, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Orders'])
class OrderDetailView(APIView):
    """Order detail endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OrderSerializer},
        summary="Get order detail",
    )
    def get(self, request, order_id: UUID):
        # TODO: Implement order detail
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(summary="Cancel order")
    def delete(self, request, order_id: UUID):
        # TODO: Implement order cancellation
        return Response(status=status.HTTP_204_NO_CONTENT)
