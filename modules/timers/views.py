"""
Timers API views.
"""
from datetime import timedelta

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.utils import timezone

from .services import TimerService, PriceHistoryService
from .serializers import (
    TimerSerializer,
    TimerListSerializer,
    TimerCreateSerializer,
    PriceHistorySerializer,
    PriceHistoryCreateSerializer,
    PriceTrendSerializer,
)


timer_service = TimerService()
history_service = PriceHistoryService()


@extend_schema(tags=['Timers'])
class TimerListCreateView(APIView):
    """List and create timers."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get price timers',
        parameters=[
            OpenApiParameter(
                name='danawa_product_id',
                type=str,
                required=False,
                description='Danawa Product ID'
            ),
            OpenApiParameter(
                name='days',
                type=int,
                required=False,
                description='Number of days to predict (default: 7)'
            ),
        ],
        responses={200: TimerListSerializer(many=True)},
    )
    def get(self, request):
        """Get timers for a product or current user."""
        danawa_product_id = request.query_params.get('danawa_product_id')
        days = int(request.query_params.get('days', 7))

        if danawa_product_id:
            timers = timer_service.get_timers_for_product(
                danawa_product_id=danawa_product_id,
                days=days
            )
        else:
            timers = timer_service.get_user_timers(
                user_id=request.user.id
            )

        serializer = TimerListSerializer(timers, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Create price timer',
        request=TimerCreateSerializer,
        responses={201: TimerSerializer},
    )
    def post(self, request):
        """Generate timer for a product."""
        serializer = TimerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        danawa_product_id = serializer.validated_data['danawa_product_id']
        target_price = serializer.validated_data['target_price']
        prediction_days = serializer.validated_data['prediction_days']

        # Create timer
        prediction_date = timezone.now() + timedelta(days=prediction_days)
        timer = timer_service.create_timer(
            danawa_product_id=danawa_product_id,
            user_id=request.user.id,
            target_price=target_price,
            prediction_date=prediction_date,
        )

        result_serializer = TimerSerializer(timer)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Timers'])
class TimerDetailView(APIView):
    """Timer detail endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get timer detail',
        responses={200: TimerSerializer},
    )
    def get(self, request, timer_id: int):
        """Get timer by ID."""
        timer = timer_service.get_timer_by_id(timer_id)
        if not timer:
            return Response(
                {'error': 'Timer not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check ownership
        if timer.user_id != request.user.id and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = TimerSerializer(timer)
        return Response(serializer.data)

    @extend_schema(
        summary='Delete timer',
    )
    def delete(self, request, timer_id: int):
        """Delete a timer."""
        timer = timer_service.get_timer_by_id(timer_id)
        if not timer:
            return Response(
                {'error': 'Timer not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check ownership
        if timer.user_id != request.user.id and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        timer_service.delete_timer(timer_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Timers'])
class PriceTrendView(APIView):
    """Get price trend analysis."""
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Get price trend',
        parameters=[
            OpenApiParameter(
                name='danawa_product_id',
                type=str,
                required=True,
                description='Danawa Product ID'
            ),
            OpenApiParameter(
                name='days',
                type=int,
                required=False,
                description='Analysis period in days (default: 30)'
            ),
        ],
        responses={200: PriceTrendSerializer},
    )
    def get(self, request):
        """Analyze price trend for a product."""
        danawa_product_id = request.query_params.get('danawa_product_id')
        days = int(request.query_params.get('days', 30))

        if not danawa_product_id:
            return Response(
                {'error': 'danawa_product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        trend = timer_service.get_price_trend(
            danawa_product_id=danawa_product_id,
            days=days
        )
        serializer = PriceTrendSerializer(trend)
        return Response(serializer.data)


@extend_schema(tags=['Price History'])
class PriceHistoryListCreateView(APIView):
    """List and create price history."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        summary='Get price history',
        parameters=[
            OpenApiParameter(
                name='danawa_product_id',
                type=str,
                required=True,
                description='Danawa Product ID'
            ),
            OpenApiParameter(
                name='days',
                type=int,
                required=False,
                description='Number of days (default: 30)'
            ),
        ],
        responses={200: PriceHistorySerializer(many=True)},
    )
    def get(self, request):
        """Get price history for a product."""
        danawa_product_id = request.query_params.get('danawa_product_id')
        days = int(request.query_params.get('days', 30))

        if not danawa_product_id:
            return Response(
                {'error': 'danawa_product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        history = history_service.get_history_by_product(
            danawa_product_id=danawa_product_id,
            days=days
        )
        serializer = PriceHistorySerializer(history, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Create price history record',
        request=PriceHistoryCreateSerializer,
        responses={201: PriceHistorySerializer},
    )
    def post(self, request):
        """Create a new price history record."""
        serializer = PriceHistoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        history = history_service.create_history(
            danawa_product_id=serializer.validated_data['danawa_product_id'],
            lowest_price=serializer.validated_data['lowest_price'],
        )

        result_serializer = PriceHistorySerializer(history)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)
