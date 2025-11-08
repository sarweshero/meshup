"""Serializers for collaborative notes."""
from rest_framework import serializers

from apps.users.serializers import UserBasicSerializer

from .models import Note, NoteCollaborator, NoteVersion


class NoteVersionSerializer(serializers.ModelSerializer):
    """Serializer for note version history."""

    edited_by = UserBasicSerializer(read_only=True)

    class Meta:
        model = NoteVersion
        fields = (
            "id",
            "version_number",
            "title",
            "content",
            "edited_by",
            "change_description",
            "created_at",
        )
        read_only_fields = ("id", "edited_by", "created_at")


class NoteCollaboratorSerializer(serializers.ModelSerializer):
    """Serializer for note collaborators."""

    user = UserBasicSerializer(read_only=True)

    class Meta:
        model = NoteCollaborator
        fields = ("id", "user", "permission", "added_at")
        read_only_fields = ("id", "added_at")


class NoteSerializer(serializers.ModelSerializer):
    """Complete serializer for notes."""

    created_by = UserBasicSerializer(read_only=True)
    last_edited_by = UserBasicSerializer(read_only=True)
    version_count = serializers.SerializerMethodField()
    collaborators = NoteCollaboratorSerializer(many=True, read_only=True)

    class Meta:
        model = Note
        fields = (
            "id",
            "title",
            "content",
            "server",
            "created_by",
            "last_edited_by",
            "version",
            "version_count",
            "is_pinned",
            "is_locked",
            "tags",
            "collaborators",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_by",
            "last_edited_by",
            "version",
            "created_at",
            "updated_at",
        )

    def get_version_count(self, obj):
        return obj.version_history.count()


class NoteCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating notes."""

    change_description = serializers.CharField(
        write_only=True, required=False, help_text="Description of changes (for version history)"
    )

    class Meta:
        model = Note
        fields = ("title", "content", "is_pinned", "is_locked", "tags", "change_description")

    def update(self, instance, validated_data):
        change_description = validated_data.pop("change_description", "")
        instance.last_edited_by = self.context["request"].user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        NoteVersion.objects.create(
            note=instance,
            version_number=instance.version,
            title=instance.title,
            content=instance.content,
            edited_by=self.context["request"].user,
            change_description=change_description or "Updated note",
        )
        return instance
