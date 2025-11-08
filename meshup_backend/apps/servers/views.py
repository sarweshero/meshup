"""Views for server management."""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import filters, permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.roles.constants import ServerPermission
from apps.roles.models import ServerMember
from apps.roles.serializers import RoleSerializer, ServerMemberRoleUpdateSerializer
from apps.roles.services import (
    assign_admin_role,
    assign_default_member_role,
    ensure_default_roles,
    list_roles_for_server,
)
from apps.roles.utils import get_server_member, require_server_permission

from .models import Server
from .serializers import ServerCreateUpdateSerializer, ServerSerializer


class ServerViewSet(viewsets.ModelViewSet):
    """Manage Meshup servers (workspaces)."""

    queryset = Server.objects.all().select_related("owner")
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ServerCreateUpdateSerializer
        return ServerSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            return queryset.filter(
                Q(is_public=True) | Q(owner=self.request.user) | Q(members__user=self.request.user)
            ).distinct()
        return queryset

    def update(self, request, *args, **kwargs):  # type: ignore[override]
        server = self.get_object()
        require_server_permission(request.user, server, ServerPermission.MANAGE_SERVER)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):  # type: ignore[override]
        server = self.get_object()
        require_server_permission(request.user, server, ServerPermission.MANAGE_SERVER)
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        server = serializer.save(owner=self.request.user)
        role_map = ensure_default_roles(server)
        membership = ServerMember.objects.create(user=self.request.user, server=server, is_owner=True)
        assign_admin_role(membership, role_map)
        server.member_count = ServerMember.objects.filter(server=server).count()
        server.save(update_fields=["member_count"])
        return server

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        server = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        output = ServerSerializer(server, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):  # type: ignore[override]
        server = self.get_object()
        require_server_permission(request.user, server, ServerPermission.MANAGE_SERVER)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        server = self.get_object()
        membership = ServerMember.objects.filter(user=request.user, server=server).first()
        if membership:
            if membership.is_banned:
                return Response({"error": "You are banned from this server."}, status=status.HTTP_403_FORBIDDEN)
            return Response({"message": "Already a member"})
        membership = ServerMember.objects.create(user=request.user, server=server)
        assign_default_member_role(membership)
        server.member_count = ServerMember.objects.filter(server=server).count()
        server.save(update_fields=["member_count"])
        return Response({"message": "Joined server successfully"})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        server = self.get_object()
        membership = ServerMember.objects.filter(user=request.user, server=server).first()
        if not membership:
            return Response({"error": "Not a member"}, status=status.HTTP_400_BAD_REQUEST)
        if membership.is_owner:
            return Response({"error": "Owner cannot leave their own server"}, status=status.HTTP_400_BAD_REQUEST)
        membership.delete()
        server.member_count = ServerMember.objects.filter(server=server).count()
        server.save(update_fields=["member_count"])
        return Response({"message": "Left server successfully"})

    @action(detail=True, methods=["get"], url_path="roles")
    def list_roles(self, request, pk=None):
        server = self.get_object()
        member = get_server_member(request.user, server)
        if (
            server.owner != request.user
            and not getattr(request.user, "is_admin", False)
            and (not member or member.is_banned)
        ):
            raise PermissionDenied("You do not have access to view roles.")
        roles = list_roles_for_server(server)
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path=r"members/(?P<member_id>[^/.]+)/roles")
    def assign_roles(self, request, pk=None, member_id=None):
        server = self.get_object()
        require_server_permission(request.user, server, ServerPermission.MANAGE_ROLES)
        member = get_object_or_404(ServerMember, id=member_id, server=server)
        if member.is_owner:
            raise PermissionDenied("Cannot modify roles for the server owner.")
        serializer = ServerMemberRoleUpdateSerializer(data=request.data, context={"server": server})
        serializer.is_valid(raise_exception=True)
        serializer.save(member=member)
        if member.roles.count() == 0:
            assign_default_member_role(member)
        response = RoleSerializer(member.roles.all(), many=True)
        return Response({"message": "Roles updated successfully", "roles": response.data})
