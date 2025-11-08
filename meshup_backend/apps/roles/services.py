"""Role-related services for Meshup."""
from __future__ import annotations

from typing import Dict, Iterable, List

from django.db import transaction

from .constants import DEFAULT_PERMISSION_DEFINITIONS, DEFAULT_ROLE_DEFINITIONS
from .models import Permission, Role, ServerMember


@transaction.atomic
def ensure_default_permissions() -> Dict[str, Permission]:
    """Ensure that the core permission set exists and return them keyed by codename."""
    permission_map: Dict[str, Permission] = {}
    for definition in DEFAULT_PERMISSION_DEFINITIONS:
        permission, _created = Permission.objects.get_or_create(
            codename=definition["codename"],
            defaults={
                "name": definition["name"],
                "description": definition["description"],
                "category": definition["category"],
                "is_dangerous": definition["is_dangerous"],
            },
        )
        permission_map[permission.codename] = permission
    return permission_map


@transaction.atomic
def ensure_default_roles(server) -> Dict[str, Role]:
    """Ensure that each server receives the default role hierarchy with permissions."""
    permissions = ensure_default_permissions()
    role_map: Dict[str, Role] = {}
    for key, definition in DEFAULT_ROLE_DEFINITIONS.items():
        role, created = Role.objects.get_or_create(
            server=server,
            role_type=definition.role_type,
            defaults={
                "name": definition.name,
                "color": definition.color,
                "is_mentionable": definition.is_mentionable,
                "is_hoisted": definition.is_hoisted,
                "position": definition.position,
            },
        )
        if created or role.permissions.count() == 0:
            permission_objects = [permissions[codename] for codename in definition.permissions]
            role.permissions.set(permission_objects)
        role_map[key] = role
    return role_map


def assign_default_member_role(membership: ServerMember, role_map: Dict[str, Role] | None = None) -> None:
    """Assign the default Member role to a server membership if available."""
    if role_map is None:
        role_map = ensure_default_roles(membership.server)
    member_role = role_map.get("member")
    if member_role:
        membership.roles.add(member_role)


def assign_admin_role(membership: ServerMember, role_map: Dict[str, Role] | None = None) -> None:
    """Assign the Admin role to the provided membership."""
    if role_map is None:
        role_map = ensure_default_roles(membership.server)
    admin_role = role_map.get("admin")
    if admin_role:
        membership.roles.add(admin_role)


def get_role_by_id(server, role_id) -> Role:
    """Return a role belonging to the provided server."""
    return server.roles.get(id=role_id)


def set_member_roles(membership: ServerMember, roles: Iterable[Role]) -> None:
    """Replace all role assignments on a server member."""
    membership.roles.set(roles)


def list_roles_for_server(server) -> List[Role]:
    """Return all roles associated with a server ordered by position."""
    return server.roles.order_by("-position", "name")
