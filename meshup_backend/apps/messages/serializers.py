"""Serializers for messaging domain."""
from django.db.models import Count
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users.serializers import UserBasicSerializer

from .models import (
    DirectMessage,
    DirectMessageMessage,
    Message,
    MessageAttachment,
    MessageReaction,
)


class MessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for message attachments."""

    class Meta:
        model = MessageAttachment
        fields = (
            "id",
            "file",
            "file_name",
            "file_size",
            "attachment_type",
            "width",
            "height",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class MessageReactionSerializer(serializers.ModelSerializer):
    """Serializer for message reactions."""

    user = UserBasicSerializer(read_only=True)

    class Meta:
        model = MessageReaction
        fields = ("id", "message", "user", "emoji", "created_at")
        read_only_fields = ("id", "created_at")


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages with full details."""

    author = UserBasicSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    reactions = MessageReactionSerializer(many=True, read_only=True)
    reply_to = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id",
            "channel",
            "author",
            "content",
            "message_type",
            "reply_to",
            "thread_id",
            "is_pinned",
            "is_edited",
            "attachments",
            "reactions",
            "created_at",
            "edited_at",
        )
        read_only_fields = ("id", "author", "is_edited", "created_at", "edited_at")

    def get_reply_to(self, obj):
        """Serialize reply_to message with basic info."""
        if obj.reply_to:
            return {
                "id": str(obj.reply_to.id),
                "author": UserBasicSerializer(obj.reply_to.author).data,
                "content": obj.reply_to.content[:100],
                "created_at": obj.reply_to.created_at,
            }
        return None

    def create(self, validated_data):
        """Create message with current user as author."""
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages."""

    attachments = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )

    class Meta:
        model = Message
        fields = ("content", "reply_to", "thread_id", "attachments")

    def create(self, validated_data):
        """Create message with attachments."""
        attachments = validated_data.pop("attachments", [])
        message = Message.objects.create(**validated_data)
        for file_obj in attachments:
            MessageAttachment.objects.create(
                message=message,
                file=file_obj,
                file_name=file_obj.name,
                file_size=file_obj.size,
                attachment_type="other",
            )
        return message


class DirectMessageSerializer(serializers.ModelSerializer):
    """Serializer for direct message channels."""

    participants = UserBasicSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=True, min_length=1
    )

    class Meta:
        model = DirectMessage
        fields = (
            "id",
            "participants",
            "last_message",
            "last_message_at",
            "created_at",
            "participant_ids",
        )
        read_only_fields = ("id", "last_message_at", "created_at")

    def get_last_message(self, obj):
        """Get last message in DM channel."""
        last_msg = obj.dm_messages.first()
        if last_msg:
            return {
                "content": last_msg.content,
                "author": UserBasicSerializer(last_msg.author).data,
                "created_at": last_msg.created_at,
            }
        return None

    def validate_participant_ids(self, value):
        request = self.context.get("request")
        current_user_id = getattr(request.user, "id", None) if request else None
        unique_ids = {str(participant_id) for participant_id in value}
        if current_user_id is not None:
            unique_ids.add(str(current_user_id))
        if len(unique_ids) < 2:
            raise serializers.ValidationError("Direct messages require at least two participants.")
        return sorted(unique_ids)

    def create(self, validated_data):
        participant_ids = validated_data.pop("participant_ids", [])
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            participant_ids.append(str(request.user.id))
        unique_ids = {str(participant_id) for participant_id in participant_ids}
        User = get_user_model()
        participants = User.objects.filter(id__in=unique_ids)
        if participants.count() < 2:
            raise serializers.ValidationError("Unable to find all participants for the direct message.")

        participant_set = {str(user.id) for user in participants}
        existing_channels = (
            DirectMessage.objects.filter(participants__id__in=participant_set)
            .annotate(participant_count=Count("participants", distinct=True))
            .filter(participant_count=len(participant_set))
        )
        for dm_channel in existing_channels:
            channel_participants = set(
                str(user_id) for user_id in dm_channel.participants.values_list("id", flat=True)
            )
            if channel_participants == participant_set:
                return dm_channel

        dm = DirectMessage.objects.create(**validated_data)
        dm.participants.set(participants)
        dm.last_message_at = timezone.now()
        dm.save(update_fields=["last_message_at"])
        return dm


class DirectMessageMessageSerializer(serializers.ModelSerializer):
    """Serializer for DM messages."""

    author = UserBasicSerializer(read_only=True)

    class Meta:
        model = DirectMessageMessage
        fields = ("id", "dm_channel", "author", "content", "is_read", "created_at")
        read_only_fields = ("id", "dm_channel", "author", "created_at")

    def create(self, validated_data):
        """Create DM message with current user as author."""
        validated_data["author"] = self.context["request"].user
        dm_channel = validated_data["dm_channel"]
        dm_channel.last_message_at = timezone.now()
        dm_channel.save(update_fields=["last_message_at"])
        return super().create(validated_data)
