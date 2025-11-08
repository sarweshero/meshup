"""Serializers for role and permission management."""
from rest_framework import serializers

from .models import Permission, Role, ServerMember


class PermissionSerializer(serializers.ModelSerializer):
    """Present permission metadata for UI consumption."""

    class Meta:
        model = Permission
        fields = ("id", "name", "codename", "description", "category", "is_dangerous")
        read_only_fields = fields


class RoleSerializer(serializers.ModelSerializer):
    """Serialize a role and its associated permissions."""

    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = (
            "id",
            "name",
            "role_type",
            "color",
            "is_mentionable",
            "is_hoisted",
            "position",
            "permissions",
        )
        read_only_fields = fields


class ServerMemberRoleUpdateSerializer(serializers.Serializer):
    """Serializer for assigning roles to server members."""

    role_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
        help_text="List of role IDs to assign to the server member.",
    )

    def validate_role_ids(self, value):
        server = self.context["server"]
        available_role_ids = set(str(role_id) for role_id in server.roles.values_list("id", flat=True))
        requested_ids = [str(role_id) for role_id in value]
        missing = [role_id for role_id in requested_ids if role_id not in available_role_ids]
        if missing:
            raise serializers.ValidationError("One or more roles do not belong to this server.")
        return value

    def save(self, **kwargs):
        member: ServerMember = kwargs["member"]
        role_ids = self.validated_data["role_ids"]
        roles = member.server.roles.filter(id__in=role_ids)
        member.roles.set(roles)
        return member
