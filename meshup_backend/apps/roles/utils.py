"""Utility helpers for Meshup role-based access control."""
from __future__ import annotations

from typing import Optional

from django.core.exceptions import ObjectDoesNotExist

from apps.servers.models import Server

from .constants import ServerPermission
from .models import ServerMember


def get_server_member(user, server: Server) -> Optional[ServerMember]:
    """Retrieve the membership for a user within a server if it exists and is active."""
    if not user.is_authenticated:
        return None
    try:
        return ServerMember.objects.select_related("server", "user").prefetch_related("roles__permissions").get(
            user=user,
            server=server,
        )
    except ObjectDoesNotExist:
        return None


def user_has_server_permission(user, server: Server, permission_codename: str) -> bool:
    """Check whether a user may perform the requested action within the server."""
    if not user.is_authenticated:
        return False
    if getattr(user, "is_admin", False):
        return True
    if server.owner_id == getattr(user, "id", None):
        return True

    membership = get_server_member(user, server)
    if not membership or membership.is_banned:
        return False
    if membership.is_owner:
        return True
    return membership.has_permission(permission_codename)


def require_server_permission(user, server: Server, permission_codename: str):
    """Raise a PermissionDenied exception when the user lacks the requested permission."""
    from rest_framework.exceptions import PermissionDenied

    if not user_has_server_permission(user, server, permission_codename):
        raise PermissionDenied("You do not have permission to perform this action in this server.")


__all__ = [
    "ServerPermission",
    "get_server_member",
    "user_has_server_permission",
    "require_server_permission",
]
