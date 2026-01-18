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
    @extend_schema(
        tags=["Users"],
        request=UserSignupSerializer,
        )
    def post(self, request):
        try:   
            serializer = UserSignupSerializer(data=request.data)

            if not serializer.is_valid():
                return Response({
                    "status": 400,
                    "message": "유효하지 않은 이메일 형식입니다." 
                }, status=status.HTTP_400_BAD_REQUEST)
            user = UserSignupService.create_user(serializer.validated_data)
            return Response({
                "status": 201,
                "message": "회원가입이 완료되었습니다.",
                "data": {
                    "user_id": user.id,
                    "email": user.email,
                    "created_at": user.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
                    }
                }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
                # 4. 명세서 500 에러: 서버 내부 오류
                return Response({
                    "status": 500,
                    "message": "서버 내부 오류가 발생했습니다."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class UserLoginview(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Users"],
        request=UserLoginSerializer,
    )
    def post(self,request):
        try:
            serializer = UserLoginSerializer(data=request.data)
            if not serializer.is_valid():
                 return Response({
                      "status":401,
                      "message": "이메일 또는 비밀번호가 일치하지 않습니다"
                 },status=status.HTTP_401_UNAUTHORIZED)
            
            user = serializer.validated_data['user']
            #토큰 생성
            token_data = UserLoginService().get_login_token(user)
            return Response({
                "status":200,
                "user_id":user.id,
                "message":"로그인 성공",
                "data":{
                    "access_token":token_data['access'],
                    "refresh_token":token_data['refresh'],
                    "token_type":"Bearer"
                }
                }, status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response({
                "status": 500,
                "message": "서버 내부 오류가 발생했습니다."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
