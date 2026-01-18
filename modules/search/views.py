"""
Search API views.
"""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse # OpenApiResponse 추가

from .services import SearchService, RecentViewProductService
from .serializers import (
    SearchQuerySerializer,
    SearchResultSerializer,
    SearchHistorySerializer,
    RecentViewProductSerializer,
    RecentViewProductCreateSerializer,
    AutocompleteResponseSerializer
)

class SearchView(APIView):
    """Main search endpoint."""
    permission_classes = [AllowAny]
    search_service = SearchService()

    @extend_schema(
        tags=['Search'],
        summary='Search products',
        request=SearchQuerySerializer,
        responses={200: SearchResultSerializer},
    )
    def post(self, request):
        serializer = SearchQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user_id = request.user.id if request.user.is_authenticated else None
        results = self.search_service.search_products(
            query=data['query'], search_mode=data['search_mode'], user_id=user_id
        )
        return Response(results)

class SearchHistoryView(APIView):
    """User search history."""
    permission_classes = [IsAuthenticated]
    search_service = SearchService()

    @extend_schema(
        tags=['Search'],
        summary='Get my search history',
        parameters=[OpenApiParameter(name='limit', type=int, required=False)],
        responses={200: SearchHistorySerializer(many=True)},
    )
    def get(self, request):
        limit = int(request.query_params.get('limit', 20))
        history = self.search_service.get_user_search_history(user_id=request.user.id, limit=limit)
        return Response(SearchHistorySerializer(history, many=True).data)

class RecentViewProductsView(APIView):
    """Recent view products endpoint."""
    permission_classes = [IsAuthenticated]
    recent_view_service = RecentViewProductService()

    @extend_schema(
        tags=['Search'],
        summary='Get my recent view products',
        parameters=[OpenApiParameter(name='limit', type=int, required=False)],
        responses={200: RecentViewProductSerializer(many=True)},
    )
    def get(self, request):
        limit = int(request.query_params.get('limit', 20))
        views = self.recent_view_service.get_user_recent_views(user_id=request.user.id, limit=limit)
        return Response(RecentViewProductSerializer(views, many=True).data)

    @extend_schema(
        tags=['Search'],
        summary='Record product view',
        request=RecentViewProductCreateSerializer,
        responses={201: RecentViewProductSerializer},
    )
    def post(self, request):
        serializer = RecentViewProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        view = self.recent_view_service.record_view(
            user_id=request.user.id, danawa_product_id=serializer.validated_data['danawa_product_id']
        )
        return Response(RecentViewProductSerializer(view).data, status=status.HTTP_201_CREATED)

class RecentViewProductDeleteView(APIView):
    """Delete recent view product endpoint."""
    permission_classes = [IsAuthenticated]
    recent_view_service = RecentViewProductService()

    @extend_schema(tags=['Search'], summary='Delete recent view product')
    def delete(self, request, danawa_product_id: str):
        self.recent_view_service.delete_recent_view(user_id=request.user.id, danawa_product_id=danawa_product_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
@extend_schema(tags=['Search'])
class AutocompleteView(APIView):
    """검색어 자동완성 API 엔드포인트"""
    permission_classes = [AllowAny]
    search_service = SearchService()

    @extend_schema(
        
        summary='Search autocomplete',
        parameters=[
            OpenApiParameter(name='keyword', type=str, description='사용자가 입력 중인 검색어', required=True),
        ],
        responses={
            # 기존 AutocompleteBaseResponseSerializer에서 임포트된 이름으로 수정
            200: AutocompleteResponseSerializer, 
            # OpenApiParameter 대신 OpenApiResponse를 사용해야 Swagger에 나타납니다
            500: OpenApiResponse(description='서버 내부 오류') 
        },
    )
    def get(self, request):
        keyword = request.query_params.get('keyword', '')
        try:
            suggestions = self.search_service.get_autocomplete_suggestions(keyword)
            return Response({
                "status": 200,
                "message": "자동완성 목록 조회 성공",
                "data": {"suggestions": suggestions}
            }, status=status.HTTP_200_OK)
        except Exception:
            return Response({
                "status": 500, "message": "서버 내부 오류가 발생했습니다."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)