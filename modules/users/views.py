from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import UserSignupSerializer,UserLoginSerializer
from .services import UserSignupService,UserLoginService
from drf_spectacular.utils import extend_schema

@extend_schema(
    tags=["Users"],
    request=UserSignupSerializer,
    )
class UserSignupView(APIView):
    """
    회원가입 API
    """
    permission_classes = [AllowAny]
    def post(self, request):
        
        serializer = UserSignupSerializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            UserSignupService.create_user(serializer.validated_data)
            return Response({
                "message": "회원가입이 완료되었습니다."
                }, status=status.HTTP_201_CREATED
                )
@extend_schema(
    tags=["Users"],
    request=UserLoginSerializer,
    )
class UserLoginview(APIView):
    permission_classes = [AllowAny]
    def post(self,request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)   
        user = serializer.validated_data['user']
        #토큰 불러오기
        token_data = UserLoginService().get_login_token(user)
        return Response({
            "message":"로그인 성공",
            "token":token_data,
            }, status=status.HTTP_200_OK
            )
