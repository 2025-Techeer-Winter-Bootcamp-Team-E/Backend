"""
Authentication serializers.
"""
from rest_framework import serializers


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
