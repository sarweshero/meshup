"""Role and permission defaults for Meshup servers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


class ServerPermission:
    """Enumerate server-level permission codenames."""

    MANAGE_SERVER = "server.manage"
    MANAGE_CHANNELS = "channel.manage"
    MANAGE_MEMBERS = "member.manage"
    MANAGE_ROLES = "role.manage"


DEFAULT_PERMISSION_DEFINITIONS = (
    {
        "codename": ServerPermission.MANAGE_SERVER,
        "name": "Manage Server",
        "description": "Update server settings, delete the server, and configure advanced options.",
        "category": "server",
        "is_dangerous": True,
    },
    {
        "codename": ServerPermission.MANAGE_CHANNELS,
        "name": "Manage Channels",
        "description": "Create, update, and delete channels within the server.",
        "category": "channel",
        "is_dangerous": False,
    },
    {
        "codename": ServerPermission.MANAGE_MEMBERS,
        "name": "Manage Members",
        "description": "Invite, remove, ban, or update members within the server.",
        "category": "member",
        "is_dangerous": True,
    },
    {
        "codename": ServerPermission.MANAGE_ROLES,
        "name": "Manage Roles",
        "description": "Create custom roles and assign permissions to members.",
        "category": "member",
        "is_dangerous": True,
    },
)


@dataclass(frozen=True)
class DefaultRoleDefinition:
    """Capture the default role metadata."""

    name: str
    role_type: str
    color: str
    permissions: List[str]
    is_mentionable: bool = True
    is_hoisted: bool = False
    position: int = 0


DEFAULT_ROLE_DEFINITIONS: Dict[str, DefaultRoleDefinition] = {
    "admin": DefaultRoleDefinition(
        name="Admin",
        role_type="admin",
        color="#5865F2",
        permissions=[
            ServerPermission.MANAGE_SERVER,
            ServerPermission.MANAGE_CHANNELS,
            ServerPermission.MANAGE_MEMBERS,
            ServerPermission.MANAGE_ROLES,
        ],
        position=400,
    ),
    "manager": DefaultRoleDefinition(
        name="Manager",
        role_type="manager",
        color="#57F287",
        permissions=[
            ServerPermission.MANAGE_CHANNELS,
            ServerPermission.MANAGE_MEMBERS,
        ],
        position=300,
    ),
    "member": DefaultRoleDefinition(
        name="Member",
        role_type="member",
        color="#EB459E",
        permissions=[],
        position=200,
    ),
    "guest": DefaultRoleDefinition(
        name="Guest",
        role_type="guest",
        color="#747F8D",
        permissions=[],
        position=100,
        is_mentionable=False,
    ),
}
