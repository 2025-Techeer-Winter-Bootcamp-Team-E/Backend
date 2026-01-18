from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import UserModel

# 1. 회원가입 데이터를 담을 그릇(Serializer)의 이름을 정합니다.
class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    # 이메일 중복 체크 로직
    def validate_email(self, value):
        """이메일이 이미 존재하는지 확인합니다."""
        if UserModel.objects.filter(email=value).exists():
            raise serializers.ValidationError("이미 존재하는 이메일입니다.")
        return value
    
    class Meta:
        model=UserModel
        fields=['email', 'password','nickname','name','phone']

class UserLoginSerializer(serializers.Serializer):
    email=serializers.EmailField()
    password=serializers.CharField(style={'input_type':'password'})
    
    def validate(self, data):
        email=data['email']
        password=data['password']
        user=authenticate(username=email,password=password)
        if user is not None:
            data['user']=user
            return data
        else:
            raise serializers.ValidationError("이메일 또는 비밀번호가 올바르지 않습니다.")


            
