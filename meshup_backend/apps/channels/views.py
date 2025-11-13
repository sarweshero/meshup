"""Channel API views."""
from django.shortcuts import get_object_or_404
from rest_framework import filters, permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.servers.models import Server
from apps.roles.constants import ServerPermission
from apps.roles.utils import get_server_member, require_server_permission

from .models import Channel
from .serializers import ChannelSerializer


class ChannelViewSet(viewsets.ModelViewSet):
    """Manage channels within servers."""

    serializer_class = ChannelSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["position", "name"]
    ordering = ["position"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Channel.objects.none()

        server_id = self.kwargs.get("server_id")
        if not server_id:
            return Channel.objects.none()

        server = get_object_or_404(Server, id=server_id)
        self._ensure_member_access(server)
        return Channel.objects.filter(server=server).select_related("server", "created_by")

    def perform_create(self, serializer):
        server = get_object_or_404(Server, id=self.kwargs.get("server_id"))
        require_server_permission(self.request.user, server, ServerPermission.MANAGE_CHANNELS)

        serializer.save(server=server, created_by=self.request.user)

    def update(self, request, *args, **kwargs):  # type: ignore[override]
        channel = self.get_object()
        require_server_permission(request.user, channel.server, ServerPermission.MANAGE_CHANNELS)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):  # type: ignore[override]
        channel = self.get_object()
        require_server_permission(request.user, channel.server, ServerPermission.MANAGE_CHANNELS)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):  # type: ignore[override]
        channel = self.get_object()
        require_server_permission(request.user, channel.server, ServerPermission.MANAGE_CHANNELS)
        return super().destroy(request, *args, **kwargs)

    def _ensure_member_access(self, server: Server) -> None:
        if server.owner == self.request.user or getattr(self.request.user, "is_admin", False):
            return
        membership = get_server_member(self.request.user, server)
        if membership and not membership.is_banned:
            return
        raise PermissionDenied("You do not have access to this server.")
