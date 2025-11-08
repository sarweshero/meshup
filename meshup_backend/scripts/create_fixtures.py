"""Populate the database with development fixtures."""
import os
import sys
from pathlib import Path

import django


def setup_django() -> None:
    """Configure Django settings for standalone script execution."""
    base_dir = Path(__file__).resolve().parent.parent
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    django.setup()


def create_sample_data() -> None:
    """Create baseline users, server, channels, and memberships."""
    from apps.roles.models import ServerMember
    from apps.roles.services import assign_admin_role, assign_default_member_role, ensure_default_roles
    from apps.servers.models import Server
    from apps.channels.models import Channel
    from apps.users.models import User

    admin = User.objects.filter(email="admin@meshup.com").first()
    if not admin:
        admin = User.objects.create_user(
            email="admin@meshup.com",
            username="admin",
            password="admin123",
            is_admin=True,
        )
    else:
        admin.is_admin = True
        update_fields = ["is_admin"]
        if not admin.has_usable_password():
            admin.set_password("admin123")
            update_fields.append("password")
        admin.save(update_fields=update_fields)

    user1 = User.objects.filter(email="john@example.com").first()
    if not user1:
        user1 = User.objects.create_user(
            email="john@example.com",
            username="john",
            password="pass123",
        )

    user2 = User.objects.filter(email="jane@example.com").first()
    if not user2:
        user2 = User.objects.create_user(
            email="jane@example.com",
            username="jane",
            password="pass123",
        )

    server, _ = Server.objects.get_or_create(
        name="Test Server",
        defaults={"description": "A test server for development", "owner": admin},
    )

    Channel.objects.get_or_create(
        server=server,
        name="general",
        defaults={
            "description": "General discussion",
            "channel_type": "text",
            "created_by": admin,
        },
    )

    Channel.objects.get_or_create(
        server=server,
        name="random",
        defaults={
            "description": "Random stuff",
            "channel_type": "text",
            "created_by": admin,
        },
    )

    role_map = ensure_default_roles(server)

    admin_membership, _ = ServerMember.objects.get_or_create(
        user=admin, server=server, defaults={"is_owner": True}
    )
    assign_admin_role(admin_membership, role_map)

    member1, _ = ServerMember.objects.get_or_create(user=user1, server=server)
    assign_default_member_role(member1, role_map)

    member2, _ = ServerMember.objects.get_or_create(user=user2, server=server)
    assign_default_member_role(member2, role_map)

    server.member_count = ServerMember.objects.filter(server=server).count()
    server.save(update_fields=["member_count"])

    print("Sample data created successfully!")


if __name__ == "__main__":
    setup_django()
    create_sample_data()
