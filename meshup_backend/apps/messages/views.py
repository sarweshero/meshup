"""ViewSets for messaging functionality."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.settings import api_settings

from apps.channels.models import Channel
from apps.roles.constants import ServerPermission
from apps.roles.utils import require_server_permission
from apps.roles.models import ServerMember
from apps.auth.throttles import MessageThrottle

from .models import DirectMessage, DirectMessageMessage, Message, MessageReaction
from .serializers import (
    DirectMessageMessageSerializer,
    DirectMessageSerializer,
    MessageCreateSerializer,
    MessageReactionSerializer,
    MessageSerializer,
)


class MessageViewSet(viewsets.ModelViewSet):
    """Manage messages within channels."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = tuple(api_settings.DEFAULT_THROTTLE_CLASSES) + (MessageThrottle,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["author", "is_pinned", "thread_id"]
    search_fields = ["content"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return MessageCreateSerializer
        return MessageSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Message.objects.none()

        channel_id = self.kwargs.get("channel_id")
        if not channel_id:
            return Message.objects.none()

        channel = get_object_or_404(Channel, id=channel_id)
        if not ServerMember.objects.filter(
            server=channel.server, user=self.request.user, is_banned=False
        ).exists() and channel.server.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You do not have access to this channel.")
        return (
            Message.objects.filter(channel=channel, is_deleted=False)
            .select_related("author", "channel")
            .prefetch_related("attachments", "reactions", "mentions")
        )

    def perform_create(self, serializer):
        channel_id = self.kwargs.get("channel_id")
        channel = get_object_or_404(Channel, id=channel_id)
        if not ServerMember.objects.filter(
            server=channel.server, user=self.request.user, is_banned=False
        ).exists() and channel.server.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You do not have permission to post in this channel.")
        return serializer.save(channel=channel, author=self.request.user)

    def perform_update(self, serializer):
        message = serializer.instance
        if message.author != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You cannot edit this message.")
        serializer.save(is_edited=True, edited_at=timezone.now())

    def perform_destroy(self, instance):
        if instance.author != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You cannot delete this message.")
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["is_deleted", "deleted_at"])

    @action(detail=True, methods=["post"])
    def react(self, request, server_id=None, channel_id=None, pk=None):
        message = self.get_object()
        emoji = request.data.get("emoji")
        if not emoji:
            return Response({"error": "Emoji is required"}, status=status.HTTP_400_BAD_REQUEST)
        reaction, created = MessageReaction.objects.get_or_create(
            message=message, user=request.user, emoji=emoji
        )
        serializer = MessageReactionSerializer(reaction, context={"request": request})
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=http_status)

    @action(detail=True, methods=["delete"])
    def unreact(self, request, server_id=None, channel_id=None, pk=None):
        message = self.get_object()
        emoji = request.query_params.get("emoji")
        if not emoji:
            return Response({"error": "Emoji is required"}, status=status.HTTP_400_BAD_REQUEST)
        reaction = MessageReaction.objects.filter(message=message, user=request.user, emoji=emoji).first()
        if reaction:
            reaction.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Reaction not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["post"])
    def pin(self, request, server_id=None, channel_id=None, pk=None):
        message = self.get_object()
        require_server_permission(request.user, message.channel.server, ServerPermission.MANAGE_CHANNELS)
        message.is_pinned = True
        message.save(update_fields=["is_pinned"])
        return Response({"message": "Message pinned successfully"})

    @action(detail=True, methods=["delete"])
    def unpin(self, request, server_id=None, channel_id=None, pk=None):
        message = self.get_object()
        require_server_permission(request.user, message.channel.server, ServerPermission.MANAGE_CHANNELS)
        message.is_pinned = False
        message.save(update_fields=["is_pinned"])
        return Response({"message": "Message unpinned successfully"})

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = self.perform_create(serializer)
        output = MessageSerializer(message, context={"request": request})
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)


class DirectMessageViewSet(viewsets.ModelViewSet):
    """Manage direct message channels and messages."""

    serializer_class = DirectMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = DirectMessage.objects.all()

    def get_queryset(self):
        return DirectMessage.objects.filter(participants=self.request.user).prefetch_related(
            "participants"
        )

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        dm_channel = self.get_object()
        if request.method == "GET":
            messages = dm_channel.dm_messages.all()
            serializer = DirectMessageMessageSerializer(messages, many=True, context={"request": request})
            return Response(serializer.data)
        serializer = DirectMessageMessageSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(dm_channel=dm_channel)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
