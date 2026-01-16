"""
Users module serializers.
"""
import re
from rest_framework import serializers

from .models import UserModel


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user output."""

    class Meta:
        model = UserModel
        fields = [
            'id',
            'email',
            'nickname',
            'token_balance',
            'social_provider',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.Serializer):
    """Serializer for user registration."""

    email = serializers.EmailField()
    name = serializers.CharField(min_length=1, max_length=50)
    nickname = serializers.CharField(min_length=2, max_length=50)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_email(self, value):
        """Validate email format."""
        if not value:
            raise serializers.ValidationError("이메일은 필수 입력 항목입니다.")
        return value

    def validate_phone(self, value):
        """Validate phone number format."""
        if value:
            # 전화번호 형식: 010-1234-5678 또는 01012345678
            phone_pattern = re.compile(r'^01[0-9]-?\d{3,4}-?\d{4}$')
            if not phone_pattern.match(value):
                raise serializers.ValidationError("유효하지 않은 전화번호 형식입니다.")
        return value


class UserUpdateSerializer(serializers.Serializer):
    """Serializer for user profile update."""

    nickname = serializers.CharField(min_length=2, max_length=50, required=False)


class LoginSerializer(serializers.Serializer):
    """Serializer for login request."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TokenSerializer(serializers.Serializer):
    """Serializer for token response."""

    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    token_type = serializers.CharField(read_only=True, default="Bearer")


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for refresh token request."""

    refresh_token = serializers.CharField()


class SocialLoginSerializer(serializers.Serializer):
    """Serializer for social login request."""

    provider = serializers.ChoiceField(choices=['google', 'kakao', 'naver'])
    social_token = serializers.CharField(write_only=True)


class TokenBalanceSerializer(serializers.Serializer):
    """Serializer for token balance update."""

    amount = serializers.IntegerField()

class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("비밀번호는 8자 이상이어야 합니다.")
        return value
