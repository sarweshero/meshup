"""Messaging models for Meshup platform."""
import uuid

from django.db import models
from django.utils import timezone


class Message(models.Model):
    """Message model for chat communications."""

    MESSAGE_TYPES = (
        ("default", "Default Message"),
        ("system", "System Message"),
        ("reply", "Reply Message"),
        ("thread", "Thread Message"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey("channels.Channel", on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="messages")
    content = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default="default")

    reply_to = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies"
    )
    thread_id = models.UUIDField(null=True, blank=True, db_index=True)

    is_pinned = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "messages"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["channel", "-created_at"]),
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["thread_id"]),
            models.Index(fields=["is_pinned"]),
        ]

    def __str__(self) -> str:
        return f"{self.author.username}: {self.content[:50]}"


class MessageAttachment(models.Model):
    """Attachment model for message files."""

    ATTACHMENT_TYPES = (
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("document", "Document"),
        ("other", "Other"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="message_attachments/")
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    attachment_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "message_attachments"

    def __str__(self) -> str:
        return f"{self.file_name} ({self.attachment_type})"


class MessageReaction(models.Model):
    """Reaction model for message emoji responses."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="message_reactions")
    emoji = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "message_reactions"
        unique_together = [["message", "user", "emoji"]]
        indexes = [
            models.Index(fields=["message", "emoji"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} reacted {self.emoji}"


class MessageMention(models.Model):
    """Mention model for @user mentions in messages."""

    MENTION_TYPES = (
        ("user", "User Mention"),
        ("role", "Role Mention"),
        ("everyone", "Everyone Mention"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="mentions")
    mention_type = models.CharField(max_length=20, choices=MENTION_TYPES)
    mentioned_user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_mentions",
    )
    mentioned_role = models.ForeignKey(
        "roles.Role",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="role_mentions",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "message_mentions"
        indexes = [
            models.Index(fields=["mentioned_user"]),
            models.Index(fields=["mentioned_role"]),
        ]


class DirectMessage(models.Model):
    """Direct message channel between users."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField("users.User", related_name="dm_channels")
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "direct_messages"
        ordering = ["-last_message_at"]

    def __str__(self) -> str:
        usernames = ", ".join([user.username for user in self.participants.all()])
        return f"DM: {usernames}"


class DirectMessageMessage(models.Model):
    """Individual messages within direct message channels."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dm_channel = models.ForeignKey(DirectMessage, on_delete=models.CASCADE, related_name="dm_messages")
    author = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="sent_dms")
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "direct_message_messages"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["dm_channel", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.author.username}: {self.content[:30]}"
