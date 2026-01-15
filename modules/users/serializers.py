"""
Users module serializers.
"""
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
    nickname = serializers.CharField(min_length=2, max_length=50)
    password = serializers.CharField(min_length=8, write_only=True)


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
    access_token = serializers.CharField()


class TokenBalanceSerializer(serializers.Serializer):
    """Serializer for token balance update."""

    amount = serializers.IntegerField()
