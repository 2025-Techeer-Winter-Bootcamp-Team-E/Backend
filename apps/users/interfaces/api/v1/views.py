"""
Users API v1 views.
"""
from uuid import UUID

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ....application.use_cases import RegisterUserUseCase, LoginUserUseCase
from ....application.dtos.user_dto import UserCreateDTO, UserDTO
from ....application.dtos.auth_dto import LoginDTO
from ....infrastructure.repositories import DjangoUserRepository
from ...serializers.user_serializer import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
)
from ...serializers.auth_serializer import (
    LoginSerializer,
    TokenSerializer,
)


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

        # Create use case
        repository = DjangoUserRepository()
        use_case = RegisterUserUseCase(user_repository=repository)

        # Execute
        input_dto = UserCreateDTO(**serializer.validated_data)
        result = use_case.execute(input_dto)

        # Return response
        output_serializer = UserSerializer(result.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


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

        # Create use case
        repository = DjangoUserRepository()
        use_case = LoginUserUseCase(user_repository=repository)

        # Execute
        input_dto = LoginDTO(**serializer.validated_data)
        result = use_case.execute(input_dto)

        # Return response
        output_serializer = TokenSerializer(result.data)
        return Response(output_serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=['Users'])
class UserMeView(APIView):
    """Current user endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserSerializer},
        summary="Get current user profile",
    )
    def get(self, request):
        repository = DjangoUserRepository()
        user = repository.find_by_id(request.user.id)
        serializer = UserSerializer(UserDTO.from_entity(user))
        return Response(serializer.data)

    @extend_schema(
        request=UserUpdateSerializer,
        responses={200: UserSerializer},
        summary="Update current user profile",
    )
    def patch(self, request):
        serializer = UserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        repository = DjangoUserRepository()
        user = repository.find_by_id(request.user.id)
        user.update_profile(**serializer.validated_data)
        saved_user = repository.save(user)

        output_serializer = UserSerializer(UserDTO.from_entity(saved_user))
        return Response(output_serializer.data)


@extend_schema(tags=['Users'])
class UserListView(APIView):
    """User list endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserSerializer(many=True)},
        summary="List all users",
    )
    def get(self, request):
        repository = DjangoUserRepository()
        users = repository.find_all()
        dtos = [UserDTO.from_entity(user) for user in users]
        serializer = UserSerializer(dtos, many=True)
        return Response(serializer.data)


@extend_schema(tags=['Users'])
class UserDetailView(APIView):
    """User detail endpoint."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserSerializer},
        summary="Get user by ID",
    )
    def get(self, request, user_id: UUID):
        repository = DjangoUserRepository()
        user = repository.find_by_id(user_id)
        if user is None:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = UserSerializer(UserDTO.from_entity(user))
        return Response(serializer.data)
