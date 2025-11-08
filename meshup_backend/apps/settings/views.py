"""Settings API views for Meshup."""
from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.servers.models import Server
from apps.roles.models import ServerMember

from .models import NotificationPreference, ServerSettings, UserSettings
from .serializers import (
    NotificationPreferenceSerializer,
    ServerSettingsSerializer,
    UserSettingsSerializer,
)


class UserSettingsViewSet(viewsets.ModelViewSet):
    """Manage settings for the authenticated user."""

    serializer_class = UserSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserSettings.objects.filter(user=self.request.user)

    def get_object(self):
        settings, _created = UserSettings.objects.get_or_create(user=self.request.user)
        return settings

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = self.get_serializer(self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ServerSettingsViewSet(viewsets.ModelViewSet):
    """Manage server-level settings."""

    serializer_class = ServerSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        server_id = self.kwargs.get("server_id")
        server = get_object_or_404(Server, id=server_id)
        settings, _created = ServerSettings.objects.get_or_create(server=server)
        if not ServerMember.objects.filter(
            server=server, user=self.request.user, is_banned=False
        ).exists() and server.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You do not have access to this server's settings.")
        return settings

    def _assert_permission(self, server_settings: ServerSettings) -> None:
        server = server_settings.server
        if server.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You do not have permission to modify these settings.")

    def retrieve(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):  # type: ignore[override]
        server_settings = self.get_object()
        self._assert_permission(server_settings)
        serializer = self.get_serializer(server_settings, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):  # type: ignore[override]
        server_settings = self.get_object()
        self._assert_permission(server_settings)
        serializer = self.get_serializer(server_settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """Manage per-server notification preferences for the authenticated user."""

    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
