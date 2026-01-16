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
    SocialLoginSerializer,
    PasswordChangeSerializer
)
from .exceptions import UserAlreadyExistsError, InvalidCredentialsError, UserInactiveError
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


@extend_schema(tags=['Users'])     

class LoginView(APIView):
    """로그인 API - 사용자의 계정 정보를 확인하고 인증 토큰을 발급"""
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'access_token': {'type': 'string', 'description': 'JWT 액세스 토큰'},
                    'refresh_token': {'type': 'string', 'description': 'JWT 리프레시 토큰'},
                    'token_type': {'type': 'string', 'description': '토큰 타입 (Bearer)', 'default': 'Bearer'},
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                },
                'example': {
                    'status': 400,
                    'message': '유효하지 않은 이메일 또는 비밀번호입니다.'
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
        summary="로그인",
        description="사용자의 계정 정보를 확인하고 인증 토큰을 발급\n\n**Request Body 예시:**\n```json\n{\n  \"email\": \"user@example.com\",\n  \"password\": \"securePassword123!\"\n}\n```"
    )
    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            result = user_service.authenticate(**serializer.validated_data)

            return Response(TokenSerializer(result).data)
        except DRFValidationError as e:
            # DRF ValidationError 처리 (필드 검증 실패)
            error_message = "유효하지 않은 입력값입니다."
            if hasattr(e, 'detail'):
                if isinstance(e.detail, dict):
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
        except InvalidCredentialsError:
            # 인증 실패 에러 처리
            return Response(
                {
                    'status': 400,
                    'message': '유효하지 않은 이메일 또는 비밀번호입니다.',
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except UserInactiveError as e:
            # 비활성화된 사용자 에러 처리
            return Response(
                {
                    'status': 400,
                    'message': '비활성화된 계정입니다.',
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # 기타 서버 에러 처리
            logger.error(f"로그인 중 서버 오류 발생: {str(e)}", exc_info=True)
            return Response(
                {
                    'status': 500,
                    'message': '서버 내부 오류가 발생했습니다.',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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


@extend_schema(tags=['Users'])
class SocialLoginView(APIView):
    """소셜 로그인 API - 카카오, 구글 등 외부 계정을 통해 로그인"""
    permission_classes = [AllowAny]

    @extend_schema(
        request=SocialLoginSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'access_token': {'type': 'string', 'description': 'JWT 액세스 토큰'},
                            'refresh_token': {'type': 'string', 'description': 'JWT 리프레시 토큰'},
                            'token_type': {'type': 'string', 'description': '토큰 타입 (Bearer)', 'default': 'Bearer'},
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
        summary="소셜 로그인",
        description="카카오, 구글 등 외부 계정을 통해 로그인\n\n**Request Body 예시:**\n```json\n{\n  \"provider\": \"kakao\",\n  \"social_token\": \"access_token_from_social_provider\"\n}\n```",
    )
    def post(self, request):
        try:
            serializer = SocialLoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            result = user_service.social_login(
                provider=serializer.validated_data['provider'],
                social_token=serializer.validated_data['social_token'],
            )

            # 성공 응답 형식: {status, message, data}
            return Response(
                {
                    'status': 200,
                    'message': '소셜 로그인이 완료되었습니다.',
                    'data': {
                        'access_token': result['access_token'],
                        'refresh_token': result['refresh_token'],
                        'token_type': result['token_type'],
                    }
                },
                status=status.HTTP_200_OK
            )
        except DRFValidationError as e:
            # DRF ValidationError 처리 (필드 검증 실패)
            error_message = "유효하지 않은 입력값입니다."
            if hasattr(e, 'detail'):
                if isinstance(e.detail, dict):
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
        except InvalidCredentialsError:
            # 인증 실패 에러 처리 (잘못된 토큰 또는 지원하지 않는 제공자)
            return Response(
                {
                    'status': 400,
                    'message': '잘못된 소셜 토큰이거나 지원하지 않는 제공자입니다.',
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except UserInactiveError:
            # 비활성화된 사용자 에러 처리
            return Response(
                {
                    'status': 400,
                    'message': '비활성화된 계정입니다.',
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # 기타 서버 에러 처리
            logger.error(f"소셜 로그인 중 서버 오류 발생: {str(e)}", exc_info=True)
            return Response(
                {
                    'status': 500,
                    'message': '서버 내부 오류가 발생했습니다.',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=['Users'])
class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PasswordChangeSerializer,
        responses={
            200: {'description': '비밀번호가 성공적으로 변경되었습니다.'},
            400: {'description': '현재 비밀번호가 일치하지 않습니다.'},
            401: {'description': '로그인이 필요합니다.'},
        },
        summary="비밀번호 변경",
        description="현재 비밀번호를 확인한 후 새로운 비밀번호로 변경합니다."
    )
    def patch(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user_service.change_password(
                user=request.user,
                current_password=serializer.validated_data['current_password'],
                new_password=serializer.validated_data['new_password'],
            )

            return Response(
                {
                    "status": 200,
                    "message": "비밀번호가 성공적으로 변경되었습니다."
                },
                status=status.HTTP_200_OK
            )

        except InvalidCredentialsError as e:
            return Response(
                {
                    "status": 400,
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

