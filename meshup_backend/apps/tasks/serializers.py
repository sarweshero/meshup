"""Serializers for task management."""
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from apps.users.serializers import UserBasicSerializer

from .models import Task, TaskAttachment, TaskComment


class TaskAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for task attachments."""

    uploaded_by = UserBasicSerializer(read_only=True)

    class Meta:
        model = TaskAttachment
        fields = ("id", "file", "file_name", "file_size", "uploaded_by", "created_at")
        read_only_fields = ("id", "uploaded_by", "created_at")


class TaskCommentSerializer(serializers.ModelSerializer):
    """Serializer for task comments."""

    author = UserBasicSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = TaskComment
        fields = (
            "id",
            "task",
            "author",
            "content",
            "reply_to",
            "replies",
            "is_edited",
            "created_at",
            "edited_at",
        )
        read_only_fields = ("id", "task", "author", "is_edited", "created_at", "edited_at")

    def get_replies(self, obj):
        if obj.replies.exists():
            return TaskCommentSerializer(obj.replies.all(), many=True, context=self.context).data
        return []


class TaskSerializer(serializers.ModelSerializer):
    """Complete serializer for tasks."""

    assigned_to = UserBasicSerializer(read_only=True)
    assigned_by = UserBasicSerializer(read_only=True)
    comments_count = serializers.SerializerMethodField()
    attachments_count = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "assigned_to",
            "assigned_by",
            "server",
            "channel",
            "status",
            "priority",
            "progress",
            "due_date",
            "start_date",
            "completed_at",
            "tags",
            "attachments",
            "comments_count",
            "attachments_count",
            "is_overdue",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "assigned_by",
            "completed_at",
            "created_at",
            "updated_at",
        )

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_attachments_count(self, obj):
        return obj.task_attachments.count()

    def get_is_overdue(self, obj):
        if obj.due_date and obj.status not in ["completed", "cancelled"]:
            return obj.due_date < timezone.now()
        return False


class TaskCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating tasks."""

    assigned_to_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Task
        fields = (
            "title",
            "description",
            "assigned_to_id",
            "channel",
            "status",
            "priority",
            "progress",
            "due_date",
            "start_date",
            "tags",
        )

    def validate(self, attrs):
        if attrs.get("due_date") and attrs.get("start_date"):
            if attrs["due_date"] < attrs["start_date"]:
                raise serializers.ValidationError({"due_date": "Due date must be after start date"})
        return attrs

    def create(self, validated_data):
        assigned_to_id = validated_data.pop("assigned_to_id", None)
        task = Task.objects.create(assigned_by=self.context["request"].user, **validated_data)
        if assigned_to_id:
            User = get_user_model()
            try:
                task.assigned_to = User.objects.get(id=assigned_to_id)
            except User.DoesNotExist as exc:
                raise serializers.ValidationError({"assigned_to_id": "Assigned user not found."}) from exc
            task.save(update_fields=["assigned_to"])
        return task

    def update(self, instance, validated_data):
        assigned_to_id = validated_data.pop("assigned_to_id", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if assigned_to_id is not None:
            User = get_user_model()
            if assigned_to_id:
                try:
                    instance.assigned_to = User.objects.get(id=assigned_to_id)
                except User.DoesNotExist as exc:
                    raise serializers.ValidationError({"assigned_to_id": "Assigned user not found."}) from exc
            else:
                instance.assigned_to = None
        instance.save()
        return instance
