"""
Search API views.
"""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .services import SearchService, RecentViewProductService
from .serializers import (
    SearchQuerySerializer,
    SearchResultSerializer,
    SearchHistorySerializer,
    RecentViewProductSerializer,
    RecentViewProductCreateSerializer,
)


class SearchView(APIView):
    """Main search endpoint."""

    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_service = SearchService()

    @extend_schema(
        tags=['Search'],
        summary='Search products',
        request=SearchQuerySerializer,
        responses={200: SearchResultSerializer},
    )
    def post(self, request):
        """Perform product search."""
        serializer = SearchQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Get user info for tracking
        user_id = None
        if request.user.is_authenticated:
            user_id = request.user.id

        results = self.search_service.search_products(
            query=data['query'],
            search_mode=data['search_mode'],
            user_id=user_id,
        )

        return Response(results)


class SearchHistoryView(APIView):
    """User search history."""

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_service = SearchService()

    @extend_schema(
        tags=['Search'],
        summary='Get my search history',
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                required=False,
                description='Number of results (default: 20)'
            ),
        ],
        responses={200: SearchHistorySerializer(many=True)},
    )
    def get(self, request):
        """Get authenticated user's search history."""
        limit = int(request.query_params.get('limit', 20))

        history = self.search_service.get_user_search_history(
            user_id=request.user.id,
            limit=limit
        )

        serializer = SearchHistorySerializer(history, many=True)
        return Response(serializer.data)


class RecentViewProductsView(APIView):
    """Recent view products endpoint."""

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.recent_view_service = RecentViewProductService()

    @extend_schema(
        tags=['Search'],
        summary='Get my recent view products',
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                required=False,
                description='Number of results (default: 20)'
            ),
        ],
        responses={200: RecentViewProductSerializer(many=True)},
    )
    def get(self, request):
        """Get authenticated user's recently viewed products."""
        limit = int(request.query_params.get('limit', 20))

        views = self.recent_view_service.get_user_recent_views(
            user_id=request.user.id,
            limit=limit
        )

        serializer = RecentViewProductSerializer(views, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Search'],
        summary='Record product view',
        request=RecentViewProductCreateSerializer,
        responses={201: RecentViewProductSerializer},
    )
    def post(self, request):
        """Record a product view."""
        serializer = RecentViewProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        view = self.recent_view_service.record_view(
            user_id=request.user.id,
            danawa_product_id=serializer.validated_data['danawa_product_id'],
        )

        return Response(
            RecentViewProductSerializer(view).data,
            status=status.HTTP_201_CREATED
        )


class RecentViewProductDeleteView(APIView):
    """Delete recent view product endpoint."""

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.recent_view_service = RecentViewProductService()

    @extend_schema(
        tags=['Search'],
        summary='Delete recent view product',
    )
    def delete(self, request, danawa_product_id: str):
        """Delete a recent view product."""
        self.recent_view_service.delete_recent_view(
            user_id=request.user.id,
            danawa_product_id=danawa_product_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
