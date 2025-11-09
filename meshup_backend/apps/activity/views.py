"""ViewSets and API endpoints for activity tracking."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ActivityLog, ActivityStreak, OnlinePresence, ShareableActivity, UserActivity
from .serializers import (
    ActivityLogSerializer,
    ActivityStreakSerializer,
    OnlinePresenceSerializer,
    ShareableActivitySerializer,
    ShareableActivityWriteSerializer,
    UpdateActivitySerializer,
    UserActivitySerializer,
)


class UserActivityViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    """ViewSet for managing user activity state."""

    queryset = UserActivity.objects.select_related("user", "server", "channel")
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    @transaction.atomic
    @action(methods=["post"], detail=False, serializer_class=UpdateActivitySerializer)
    def update_state(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_activity, _ = UserActivity.objects.select_for_update().get_or_create(user=request.user)

        data = serializer.validated_data
        if "status" in data:
            user_activity.status = data["status"]
        if "current_activity" in data:
            user_activity.current_activity = data["current_activity"]
        if data.get("current_activity") == "custom":
            user_activity.custom_activity_text = data.get("custom_activity_text", "")
            user_activity.custom_activity_emoji = data.get("custom_activity_emoji", "")
        user_activity.channel_id = data.get("channel_id")
        user_activity.last_seen = timezone.now()
        if not user_activity.activity_started_at:
            user_activity.activity_started_at = user_activity.last_seen
        user_activity.save(update_fields=[
            "status",
            "current_activity",
            "custom_activity_text",
            "custom_activity_emoji",
            "channel_id",
            "last_seen",
            "activity_started_at",
        ])

        return Response(UserActivitySerializer(user_activity).data)

    @action(methods=["post"], detail=False)
    def heartbeat(self, request, *args, **kwargs):
        user_activity, _ = UserActivity.objects.get_or_create(user=request.user)
        user_activity.last_seen = timezone.now()
        user_activity.save(update_fields=["last_seen"])
        return Response({"status": "ok"})

    @action(methods=["get"], detail=False)
    def me(self, request, *args, **kwargs):
        activity, _ = UserActivity.objects.get_or_create(user=request.user)
        return Response(UserActivitySerializer(activity).data)


class ActivityLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """ViewSet for activity logs."""

    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ActivityLog.objects.filter(user=self.request.user).order_by("-created_at")


class ActivityStreakViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """ViewSet for user streaks."""

    serializer_class = ActivityStreakSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ActivityStreak.objects.filter(user=self.request.user)


class ShareableActivityViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Manage shareable activities for the authenticated user."""

    serializer_class = ShareableActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ShareableActivity.objects.filter(user=self.request.user).order_by("-updated_at")

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ShareableActivityWriteSerializer
        return ShareableActivitySerializer

    def get_queryset(self):
        return ShareableActivity.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied("Cannot delete another user's activity.")
        super().perform_destroy(instance)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        existing = ShareableActivity.objects.filter(user=request.user).first()
        if existing:
            instance = serializer.update(existing, serializer.validated_data)
            read_serializer = ShareableActivitySerializer(instance)
            return Response(read_serializer.data, status=status.HTTP_200_OK)
        instance = serializer.save()
        read_serializer = ShareableActivitySerializer(instance)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        read_serializer = ShareableActivitySerializer(instance)
        return Response(read_serializer.data)

    @action(methods=["get"], detail=False)
    def current(self, request, *args, **kwargs):
        activity = ShareableActivity.objects.filter(user=request.user).first()
        if not activity:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(ShareableActivitySerializer(activity).data)


class OnlinePresenceViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    """View online presence sessions for the user."""

    serializer_class = OnlinePresenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = OnlinePresence.objects.filter(user=self.request.user).order_by("-came_online_at")
        return qs

    @action(methods=["post"], detail=False)
    def come_online(self, request, *args, **kwargs):
        presence = OnlinePresence.objects.create(user=request.user, came_online_at=timezone.now(), is_online=True)
        return Response(OnlinePresenceSerializer(presence).data, status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=False)
    def go_offline(self, request, *args, **kwargs):
        presence = OnlinePresence.objects.filter(user=request.user, is_online=True).order_by("-came_online_at").first()
        if not presence:
            return Response({"detail": "No active session."}, status=status.HTTP_400_BAD_REQUEST)

        presence.is_online = False
        presence.went_offline_at = timezone.now()
        presence.save(update_fields=["is_online", "went_offline_at"])
        return Response(OnlinePresenceSerializer(presence).data)
