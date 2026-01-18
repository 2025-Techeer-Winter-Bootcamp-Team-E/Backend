"""
Price Prediction API views.
"""
from datetime import timedelta

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.utils import timezone

from .services import PricePredictionService, PriceHistoryService
from .serializers import (
    PricePredictionSerializer,
    PricePredictionListSerializer,
    PricePredictionCreateSerializer,
    PriceHistorySerializer,
    PriceHistoryCreateSerializer,
    PriceTrendSerializer,
)


prediction_service = PricePredictionService()
history_service = PriceHistoryService()


@extend_schema(tags=['Price Prediction'])
class PredictionListCreateView(APIView):
    """List and create predictions."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get price predictions',
        parameters=[
            OpenApiParameter(
                name='product_id',
                type=int,
                required=False,
                description='Product ID'
            ),
            OpenApiParameter(
                name='days',
                type=int,
                required=False,
                description='Number of days to predict (default: 7)'
            ),
        ],
        responses={200: PricePredictionListSerializer(many=True)},
    )
    def get(self, request):
        """Get predictions for a product or current user."""
        product_id = request.query_params.get('product_id')
        days = int(request.query_params.get('days', 7))

        if product_id:
            predictions = prediction_service.get_predictions_for_product(
                product_id=int(product_id),
                days=days
            )
        else:
            predictions = prediction_service.get_user_predictions(
                user_id=request.user.id
            )

        serializer = PricePredictionListSerializer(predictions, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Create price prediction',
        request=PricePredictionCreateSerializer,
        responses={201: PricePredictionSerializer},
    )
    def post(self, request):
        """Generate prediction for a product."""
        serializer = PricePredictionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        target_price = serializer.validated_data['target_price']
        prediction_days = serializer.validated_data['prediction_days']

        # Check if product exists
        from modules.products.services import ProductService
        product_service = ProductService()
        product = product_service.get_product_by_id(product_id)

        if not product:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create prediction
        prediction_date = timezone.now() + timedelta(days=prediction_days)
        prediction = prediction_service.create_prediction(
            product_id=product_id,
            user_id=request.user.id,
            target_price=target_price,
            prediction_date=prediction_date,
        )

        result_serializer = PricePredictionSerializer(prediction)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Price Prediction'])
class PredictionDetailView(APIView):
    """Prediction detail endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get prediction detail',
        responses={200: PricePredictionSerializer},
    )
    def get(self, request, prediction_id: int):
        """Get prediction by ID."""
        prediction = prediction_service.get_prediction_by_id(prediction_id)
        if not prediction:
            return Response(
                {'error': 'Prediction not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check ownership
        if prediction.user_id != request.user.id and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PricePredictionSerializer(prediction)
        return Response(serializer.data)

    @extend_schema(
        summary='Delete prediction',
    )
    def delete(self, request, prediction_id: int):
        """Delete a prediction."""
        prediction = prediction_service.get_prediction_by_id(prediction_id)
        if not prediction:
            return Response(
                {'error': 'Prediction not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check ownership
        if prediction.user_id != request.user.id and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        prediction_service.delete_prediction(prediction_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Price Prediction'])
class PriceTrendView(APIView):
    """Get price trend analysis."""
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Get price trend',
        parameters=[
            OpenApiParameter(
                name='product_id',
                type=int,
                required=True,
                description='Product ID'
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
        product_id = request.query_params.get('product_id')
        days = int(request.query_params.get('days', 30))

        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        trend = prediction_service.get_price_trend(
            product_id=int(product_id),
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
                name='product_id',
                type=int,
                required=True,
                description='Product ID'
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
        product_id = request.query_params.get('product_id')
        days = int(request.query_params.get('days', 30))

        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        history = history_service.get_history_by_product(
            product_id=int(product_id),
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
            product_id=serializer.validated_data['product_id'],
            lowest_price=serializer.validated_data['lowest_price'],
        )

        result_serializer = PriceHistorySerializer(history)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)
