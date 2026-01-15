"""
Users module API views.
"""
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import UserService
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    LoginSerializer,
    TokenSerializer,
    TokenBalanceSerializer,
)


user_service = UserService()


@extend_schema(tags=['Auth'])
class RegisterView(APIView):
    """User registration endpoint."""
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserCreateSerializer,
        responses={201: UserSerializer},
        summary="Register a new user",
    )
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = user_service.register_user(**serializer.validated_data)

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['Auth'])
class LoginView(APIView):
    """User login endpoint."""
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: TokenSerializer},
        summary="Login and get tokens",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = user_service.authenticate(**serializer.validated_data)

        return Response(TokenSerializer(result).data)


@extend_schema(tags=['Users'])
class UserMeView(APIView):
    """Current user endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserSerializer},
        summary="Get current user profile",
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        request=UserUpdateSerializer,
        responses={200: UserSerializer},
        summary="Update current user profile",
    )
    def patch(self, request):
        serializer = UserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        user = user_service.update_profile(
            user_id=request.user.id,
            **serializer.validated_data
        )

        return Response(UserSerializer(user).data)


@extend_schema(tags=['Users'])
class UserListView(APIView):
    """User list endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserSerializer(many=True)},
        summary="List all users",
    )
    def get(self, request):
        users = user_service.get_all_users()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


@extend_schema(tags=['Users'])
class UserDetailView(APIView):
    """User detail endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserSerializer},
        summary="Get user by ID",
    )
    def get(self, request, user_id: int):
        user = user_service.get_user_by_id(user_id)
        if user is None:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(UserSerializer(user).data)


@extend_schema(tags=['Users'])
class UserTokenBalanceView(APIView):
    """User token balance endpoint."""
    permission_classes = [IsAdminUser]

    @extend_schema(
        request=TokenBalanceSerializer,
        responses={200: UserSerializer},
        summary="Update user token balance",
    )
    def patch(self, request, user_id: int):
        serializer = TokenBalanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = user_service.update_token_balance(
            user_id=user_id,
            amount=serializer.validated_data['amount'],
        )

        return Response(UserSerializer(user).data)
