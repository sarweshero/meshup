# Generated manually for ServerInvite model
import django.db.models.deletion
import uuid
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("servers", "0002_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServerInvite",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("code", models.CharField(max_length=16, unique=True, db_index=True)),
                ("label", models.CharField(blank=True, max_length=120)),
                ("invitee_email", models.EmailField(blank=True, max_length=254)),
                (
                    "max_uses",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Leave empty for unlimited",
                        null=True,
                    ),
                ),
                ("uses", models.PositiveIntegerField(default=0)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=timezone.now)),
                (
                    "inviter",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sent_invites",
                        to="users.user",
                    ),
                ),
                (
                    "server",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="invites",
                        to="servers.server",
                    ),
                ),
            ],
            options={
                "db_table": "server_invites",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="serverinvite",
            index=models.Index(fields=["server", "created_at"], name="server_invites_server_created_idx"),
        ),
        migrations.AddIndex(
            model_name="serverinvite",
            index=models.Index(fields=["code"], name="server_invites_code_idx"),
        ),
    ]
