"""
Category serializers.
"""
from rest_framework import serializers


class CategorySerializer(serializers.Serializer):
    """Serializer for category output."""
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    parent_id = serializers.UUIDField(read_only=True, allow_null=True)
    is_active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class CategoryCreateSerializer(serializers.Serializer):
    """Serializer for category creation."""
    name = serializers.CharField(min_length=2, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    parent_id = serializers.UUIDField(required=False, allow_null=True)
