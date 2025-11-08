"""Serializers for user-related operations."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Lightweight user representation for nested responses."""

    class Meta:
        model = User
        fields = ("id", "username", "discriminator", "status", "avatar")
        read_only_fields = fields


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for user profiles."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "discriminator",
            "avatar",
            "bio",
            "status",
            "custom_status",
            "is_verified",
            "date_joined",
            "last_login",
        )
        read_only_fields = (
            "id",
            "email",
            "username",
            "discriminator",
            "is_verified",
            "date_joined",
            "last_login",
        )
