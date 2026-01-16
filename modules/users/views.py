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
    PasswordChangeSerializer,
    RecentlyViewedProductSerializer,
    WishlistProductSerializer,
    CartItemSerializer,
    PurchaseTimerSerializer,
)
from .exceptions import UserAlreadyExistsError, InvalidCredentialsError, UserInactiveError
from shared.exceptions import ValidationError
from modules.search.services import RecentViewService
from modules.orders.services import StorageService
from modules.price_prediction.services import PricePredictionService
from modules.products.serializers import ProductListSerializer
from modules.search.serializers import RecentViewSerializer
from modules.orders.serializers import StorageItemSerializer

logger = logging.getLogger(__name__)


user_service = UserService()
recent_view_service = RecentViewService()
storage_service = StorageService()
price_prediction_service = PricePredictionService()

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

@extend_schema(tags=['Users'])
class UserDeleteView(APIView):
    """회원 탈퇴 API - 로그인한 사용자를 Soft Delete 처리"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: {'description': '회원 탈퇴 처리가 완료되었습니다.'},
            401: {'description': '로그인이 필요합니다.'},
            500: {'description': '서버 내부 오류가 발생했습니다.'},
        },
        summary="회원 탈퇴",
        description="로그인한 사용자를 Soft Delete 처리하고 is_active를 False로 변경합니다."
    )
    def delete(self, request):
        try:
            user = request.user

            # 이미 탈퇴된 경우도 그냥 처리
            user_service.delete_user(user.id)

            return Response(
                {
                    "status": 200,
                    "message": "회원 탈퇴 처리가 완료되었습니다."
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"회원 탈퇴 중 서버 오류 발생: {str(e)}", exc_info=True)
            return Response(
                {
                    "status": 500,
                    "message": "서버 내부 오류가 발생했습니다."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



@extend_schema(tags=['Users'])
class FavoriteProductsView(APIView):
    """사용자가 관심 등록한 상품 리스트 조회"""
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
                                'wishlist_id': {'type': 'integer'},
                                'product_id': {'type': 'integer'},
                                'product_name': {'type': 'string'},
                                'price': {'type': 'integer'},
                                'added_at': {'type': 'string', 'format': 'date-time'},
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
        summary="관심 상품 조회",
        description="사용자가 '좋아요' 또는 '관심 상품'으로 등록한 목록을 조회",
    )
    def get(self, request):
        try:
            products = user_service.get_favorite_products(request.user.id)
            
            # 요구사항에 맞는 형식으로 데이터 변환
            # favorite_products ManyToMany 관계를 사용한다고 가정
            # ManyToMany 관계 테이블에서 추가된 날짜를 가져와야 함
            data = []
            user = request.user
            
            # ManyToMany 관계를 통해 상품과 추가된 날짜를 가져옴
            # through 모델이 있다면 그것을 사용하고, 없다면 생성 날짜 사용
            if hasattr(user, 'favorite_products'):
                # through 모델이 있는 경우 (예: UserFavoriteProduct)
                # 일단 현재 구조에서는 직접 조회하는 방식 사용
                favorite_products = user.favorite_products.all()
                
                # ManyToMany through 모델이 있는지 확인
                # 없다면 기본 through 테이블의 ID와 created_at을 사용할 수 없음
                # 이 경우 임시로 인덱스와 상품 생성 날짜 사용
                for idx, product in enumerate(favorite_products):
                    # wishlist_id는 관계 테이블의 ID이지만, 기본 ManyToMany는 직접 접근 불가
                    # through 모델이 있다면 through 모델의 ID를 사용해야 함
                    data.append({
                        'wishlist_id': idx + 1,  # 실제로는 through 모델의 ID 사용 필요
                        'product_id': product.id,
                        'product_name': product.name,
                        'price': product.lowest_price,
                        'added_at': product.created_at.isoformat() if product.created_at else None,
                    })
            
            return Response({
                "status": 200,
                "message": "관심 상품 목록 조회 성공",
                "data": data
            })
        except Exception as e:
            logger.error(f"관심 상품 조회 중 서버 오류 발생: {str(e)}", exc_info=True)
            return Response({
                "status": 500,
                "message": "서버 내부 오류가 발생했습니다."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(tags=['Users'])
class RecentlyViewedProductsView(APIView):
    """최근 본 상품 조회 API - 사용자가 최근에 조회한 상품 리스트를 가져옴"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                required=False,
                description='조회할 상품 개수 (기본값: 20)'
            ),
        ],
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
                                'product_id': {'type': 'integer'},
                                'product_name': {'type': 'string'},
                                'thumbnail_url': {'type': 'string', 'nullable': True},
                                'viewed_at': {'type': 'string', 'format': 'date-time'},
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
        summary="최근 본 상품 조회",
        description="사용자가 최근에 조회한 상품 리스트를 가져옴",
    )
    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 20))
            
            recent_views = recent_view_service.get_user_recent_views(
                user_id=request.user.id,
                limit=limit
            )
            
            # 요구사항에 맞는 형식으로 데이터 변환
            data = []
            for view in recent_views:
                # thumbnail_url은 MallInformation의 representative_image_url 사용
                thumbnail_url = None
                if hasattr(view.product, 'mall_information') and view.product.mall_information.exists():
                    first_mall = view.product.mall_information.filter(deleted_at__isnull=True).first()
                    if first_mall:
                        thumbnail_url = first_mall.representative_image_url
                
                data.append({
                    'product_id': view.product_id,
                    'product_name': view.product.name,
                    'thumbnail_url': thumbnail_url,
                    'viewed_at': view.updated_at.isoformat() if view.updated_at else view.created_at.isoformat(),
                })
            
            return Response(
                {
                    'status': 200,
                    'message': '최근 본 상품 조회 성공',
                    'data': data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"최근 본 상품 조회 중 서버 오류 발생: {str(e)}", exc_info=True)
            return Response(
                {
                    'status': 500,
                    'message': '서버 내부 오류가 발생했습니다.',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=['Users'])
class CartListView(APIView):
    """장바구니 목록 조회 API - 구매를 위해 장바구니에 담은 상품 목록을 조회"""
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
        summary="장바구니 목록 조회",
        description="구매를 위해 장바구니에 담은 상품 목록을 조회",
    )
    def get(self, request):
        try:
            storage_items = storage_service.get_user_storage_items(request.user.id)
            
            # 요구사항에 맞는 형식으로 데이터 변환
            data = []
            for item in storage_items:
                price = item.product.lowest_price if item.product else 0
                total_price = price * item.quantity
                
                data.append({
                    'cart_item_id': item.id,
                    'product_id': item.product_id,
                    'product_name': item.product.name if item.product else '',
                    'quantity': item.quantity,
                    'price': price,
                    'total_price': total_price,
                })
            
            return Response(
                {
                    'status': 200,
                    'message': '장바구니 목록 조회 성공',
                    'data': data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"장바구니 목록 조회 중 서버 오류 발생: {str(e)}", exc_info=True)
            return Response(
                {
                    'status': 500,
                    'message': '서버 내부 오류가 발생했습니다.',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=['Users'])
class PurchaseTimersView(APIView):
    """구매 타이머 목록 조회 API - 상품 상세 페이지에서 설정하여 보관함에 저장된 적정 구매 타이머 리스트를 조회"""
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
                                'timer_id': {'type': 'integer'},
                                'product_id': {'type': 'integer'},
                                'product_name': {'type': 'string'},
                                'target_price': {'type': 'integer'},
                                'remaining_time': {'type': 'string'},
                                'is_expired': {'type': 'boolean'},
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
                },
                'example': {
                    'status': 401,
                    'message': '로그인이 필요합니다.'
                }
            },
            500: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'integer'},
                    'message': {'type': 'string'},
                },
                'example': {
                    'status': 500,
                    'message': '서버 내부 오류가 발생했습니다.'
                }
            }
        },
        summary="구매 타이머 목록 조회",
        description="상품 상세 페이지에서 설정하여 보관함에 저장된 적정 구매 타이머 리스트를 조회",
    )
    def get(self, request):
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            # 사용자의 활성화된 구매 타이머(예측) 목록 조회
            predictions = price_prediction_service.get_user_predictions(
                user_id=request.user.id,
                is_active=True,
                limit=100  # 충분히 큰 값으로 설정
            )
            
            now = timezone.now()
            data = []
            
            for prediction in predictions:
                # prediction_date를 만료 시간으로 사용
                expires_at = prediction.prediction_date
                
                # 만료 여부 확인
                is_expired = now >= expires_at
                
                # 남은 시간 계산 (HH:MM:SS 형식)
                if is_expired:
                    remaining_time = "00:00:00"
                else:
                    time_diff = expires_at - now
                    total_seconds = int(time_diff.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    remaining_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                
                data.append({
                    'timer_id': prediction.id,
                    'product_id': prediction.product.id,
                    'product_name': prediction.product.name,
                    'target_price': prediction.target_price,
                    'remaining_time': remaining_time,
                    'is_expired': is_expired,
                })
            
            return Response(
                {
                    'status': 200,
                    'message': '구매 타이머 목록 조회 성공',
                    'data': data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"구매 타이머 목록 조회 중 서버 오류 발생: {str(e)}", exc_info=True)
            return Response(
                {
                    'status': 500,
                    'message': '서버 내부 오류가 발생했습니다.',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )