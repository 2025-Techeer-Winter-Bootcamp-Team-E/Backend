"""
Users module API views.
"""
import logging
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError as DRFValidationError

from .services import UserService
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    LoginSerializer,
    TokenSerializer,
    TokenBalanceSerializer,
)
from .exceptions import UserAlreadyExistsError
from shared.exceptions import ValidationError

logger = logging.getLogger(__name__)


user_service = UserService()


@extend_schema(tags=['Users'])
class SignupView(APIView):
    """회원가입 API - 사용자의 정보를 입력받아 신규 계정을 생성"""
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserCreateSerializer,
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'memberId': {'type': 'integer'},
                            'email': {'type': 'string'},
                            'created_at': {'type': 'string', 'format': 'date-time'},
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
            500: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                }
            }
        },
        summary="회원가입",
        description="사용자의 정보를 입력받아 신규 계정을 생성",
    )
    def post(self, request):
        try:
            serializer = UserCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = user_service.register_user(**serializer.validated_data)

            # 성공 응답 형식: {status, message, data}
            return Response(
                {
                    'status': 201,
                    'message': '회원가입이 완료되었습니다.',
                    'data': {
                        'memberId': user.id,
                        'email': user.email,
                        'created_at': user.created_at.isoformat() if user.created_at else None,
                    }
                },
                status=status.HTTP_201_CREATED
            )
        except DRFValidationError as e:
            # DRF ValidationError 처리 (필드 검증 실패)
            error_message = "유효하지 않은 입력값입니다."
            if hasattr(e, 'detail'):
                if isinstance(e.detail, dict):
                    # 필드별 에러 메시지 추출
                    for field, messages in e.detail.items():
                        if isinstance(messages, list) and messages:
                            error_message = messages[0]
                            break
                elif isinstance(e.detail, list) and e.detail:
                    error_message = e.detail[0]
            
            return Response(
                {
                    'status': 400,
                    'message': error_message,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            # 커스텀 ValidationError 처리
            error_message = e.message
            if e.field == 'email':
                error_message = "유효하지 않은 이메일 형식입니다."
            elif e.field == 'phone_number':
                error_message = "유효하지 않은 전화번호 형식입니다."
            
            return Response(
                {
                    'status': 400,
                    'message': error_message,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except UserAlreadyExistsError as e:
            # 중복 사용자 에러 처리
            if e.field == 'email':
                error_message = "이미 사용 중인 이메일입니다."
            elif e.field == 'nickname':
                error_message = "이미 사용 중인 닉네임입니다."
            else:
                error_message = e.message
            
            return Response(
                {
                    'status': 400,
                    'message': error_message,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # 기타 서버 에러 처리
            logger.error(f"회원가입 중 서버 오류 발생: {str(e)}", exc_info=True)
            return Response(
                {
                    'status': 500,
                    'message': '서버 내부 오류가 발생했습니다.',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
