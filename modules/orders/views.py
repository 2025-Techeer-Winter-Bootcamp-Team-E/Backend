"""
Orders module API views.
"""
import logging
from datetime import datetime
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
    TokenRechargeSerializer,
    TokenPurchaseSerializer,
)
from .exceptions import InvalidRechargeAmountError, InsufficientTokenBalanceError, OrderNotFoundError
from modules.products.exceptions import ProductNotFoundError
from modules.products.services import ProductService


logger = logging.getLogger(__name__)

cart_service = CartService()
order_service = OrderService()
order_history_service = OrderHistoryService()
review_service = ReviewService()


@extend_schema(tags=['Orders'])
class CartItemListCreateView(APIView):
    """Cart item list and create endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'cart_item_id': {'type': 'integer'},
                                'product_id': {'type': 'integer'},
                                'product_name': {'type': 'string'},
                                'product_resentative_image_url': {'type': 'string'},
                                'quantity': {'type': 'integer'},
                                'price': {'type': 'integer'},
                                'total_price': {'type': 'integer'},
                            }
                        }
                    }
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                }
            },
            500: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                }
            }
        },
        summary="Get current user's cart items",
        description="장바구니 목록 조회",
    )
    def get(self, request):
        try:
            cart = cart_service.get_or_create_cart(request.user.id)
            items = cart_service.get_cart_items(cart.id)
            
            result = []
            for item in items:
                product = item.product
                if not product:
                    continue
                
                # Get representative image URL from mall_information
                representative_image_url = ''
                try:
                    mall_info = product.mall_information.filter(
                        deleted_at__isnull=True
                    ).first()
                    if mall_info and mall_info.representative_image_url:
                        representative_image_url = mall_info.representative_image_url
                except Exception:
                    pass
                
                # Use lowest_price as price
                price = product.lowest_price or 0
                total_price = price * item.quantity
                
                result.append({
                    'cart_item_id': item.id,
                    'product_id': product.id,
                    'product_name': product.name,
                    'product_resentative_image_url': representative_image_url,
                    'quantity': item.quantity,
                    'price': price,
                    'total_price': total_price,
                })
            
            return Response(
                {
                    'status': 200,
                    'message': '장바구니 목록 조회 성공',
                    'data': result,
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"장바구니 조회 중 서버 오류 발생: {str(e)}", exc_info=True)
            return Response(
                {
                    'status': 500,
                    'message': '서버 내부 오류가 발생했습니다.',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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


@extend_schema(tags=['Orders'])
class CartItemDeleteView(APIView):
    """Cart item delete endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                }
            },
            404: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                }
            },
            500: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                }
            }
        },
        summary="Remove item from cart",
        description="장바구니에서 상품 삭제",
    )
    def delete(self, request, product_id: int):
        try:
            cart = cart_service.get_or_create_cart(request.user.id)
            removed = cart_service.remove_item(cart.id, product_id)
            
            if not removed:
                return Response(
                    {
                        'status': 404,
                        'message': '잘못된 요청이거나 장바구니에 해당 상품이 없습니다.',
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(
                {
                    'status': 200,
                    'message': '장바구니에서 상품이 삭제되었습니다.',
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"장바구니 삭제 중 서버 오류 발생: {str(e)}", exc_info=True)
            return Response(
                {
                    'status': 500,
                    'message': '서버 내부 오류가 발생했습니다.',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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


@extend_schema(tags=['Orders'])
class TokenRechargeView(APIView):
    """Token recharge endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TokenRechargeSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'current_tokens': {'type': 'integer'},
                        }
                    }
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                }
            }
        },
        summary="Recharge tokens",
        description="결제를 위한 토큰 충전",
    )
    def post(self, request):
        serializer = TokenRechargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recharge_amount = serializer.validated_data['recharge_token']

        try:
            new_balance = order_history_service.recharge_token(
                user_id=request.user.id,
                recharge_amount=recharge_amount,
            )

            order_history_service.create_order_history(
                user_id=request.user.id,
                transaction_type='charge',
                token_change=recharge_amount,
                token_balance_after=new_balance,
                danawa_product_id='',
            )

            # Format the amount with commas for the message
            formatted_amount = f"{recharge_amount:,}"

            return Response(
                {
                    'status': 200,
                    'message': f"{formatted_amount} 토큰이 성공적으로 충전되었습니다.",
                    'data': {
                        'current_tokens': new_balance,
                    }
                },
                status=status.HTTP_200_OK
            )
        except InvalidRechargeAmountError as e:
            return Response(
                {
                    'status': 400,
                    'message': e.message,
                },
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(tags=['Orders'])
class TokenBalanceView(APIView):
    """Token balance inquiry endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'current_tokens': {'type': 'integer'},
                        }
                    }
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                }
            }
        },
        summary="Get token balance",
        description="현재 사용자의 토큰 잔액 조회",
    )
    def get(self, request):
        current_balance = request.user.token_balance or 0

        return Response(
            {
                'status': 200,
                'message': '토큰 잔액 조회가 완료되었습니다.',
                'data': {
                    'current_tokens': current_balance,
                }
            },
            status=status.HTTP_200_OK
        )


@extend_schema(tags=['Orders'])
class TokenPurchaseView(APIView):
    """Token purchase endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TokenPurchaseSerializer,
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'order_id': {'type': 'string'},
                            'product_name': {'type': 'string'},
                            'total_price': {'type': 'integer'},
                            'current_tokens': {'type': 'integer'},
                            'order_status': {'type': 'string'},
                            'ordered_at': {'type': 'string'},
                        }
                    }
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                }
            },
            402: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                }
            },
            404: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                }
            }
        },
        summary="Purchase product with tokens",
        description="토큰을 사용하여 상품 구매",
    )
    def post(self, request):
        serializer = TokenPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        total_price = serializer.validated_data['total_price']

        try:
            order, new_balance, product = order_history_service.purchase_with_tokens(
                user_id=request.user.id,
                product_id=product_id,
                quantity=quantity,
                total_price=total_price,
            )

            # Format order_id: ORD-YYYYMMDD-XXX (XXX는 order.id를 3자리로 포맷)
            order_date = order.created_at.strftime('%Y%m%d')
            order_id_formatted = f"ORD-{order_date}-{str(order.id).zfill(3)}"
            ordered_at = order.created_at.isoformat()

            return Response(
                {
                    'status': 201,
                    'message': '결제가 완료되었습니다.',
                    'data': {
                        'order_id': order_id_formatted,
                        'product_name': product.name,
                        'total_price': total_price,
                        'current_tokens': new_balance,
                        'order_status': 'success',
                        'ordered_at': ordered_at,
                    }
                },
                status=status.HTTP_201_CREATED
            )
        except InsufficientTokenBalanceError as e:
            return Response(
                {
                    'status': 402,
                    'message': '토큰 잔액이 부족합니다.',
                },
                status=402  # Payment Required
            )
        except OrderNotFoundError as e:
            # Check if it's a product not found error
            if 'Product' in str(e):
                return Response(
                    {
                        'status': 404,
                        'message': '상품 정보를 찾을 수 없습니다.',
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            # For other OrderNotFoundError cases
            return Response(
                {
                    'status': 404,
                    'message': str(e.message),
                },
                status=status.HTTP_404_NOT_FOUND
            )
