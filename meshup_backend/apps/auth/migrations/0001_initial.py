"""Initial migration for auth audit logging models."""
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(choices=[
                    ("login", "User Login"),
                    ("logout", "User Logout"),
                    ("password_change", "Password Changed"),
                    ("password_reset", "Password Reset"),
                    ("resource_create", "Resource Created"),
                    ("resource_update", "Resource Updated"),
                    ("resource_delete", "Resource Deleted"),
                    ("permission_grant", "Permission Granted"),
                    ("permission_revoke", "Permission Revoked"),
                    ("server_settings", "Server Settings Modified"),
                    ("role_modified", "Role Modified"),
                    ("member_ban", "Member Banned"),
                    ("member_kick", "Member Kicked"),
                    ("failed_login", "Failed Login Attempt"),
                ], db_index=True, max_length=50)),
                ("severity", models.CharField(choices=[
                    ("info", "Informational"),
                    ("warning", "Warning"),
                    ("critical", "Critical"),
                ], default="info", max_length=20)),
                ("resource_type", models.CharField(max_length=50)),
                ("resource_id", models.UUIDField(blank=True, null=True)),
                ("resource_name", models.CharField(blank=True, max_length=255)),
                ("old_values", models.JSONField(blank=True, default=dict)),
                ("new_values", models.JSONField(blank=True, default=dict)),
                ("change_description", models.TextField(blank=True)),
                ("ip_address", models.GenericIPAddressField()),
                ("user_agent", models.TextField(max_length=500)),
                ("method", models.CharField(max_length=10)),
                ("endpoint", models.CharField(max_length=255)),
                ("status_code", models.IntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(db_index=True, default=timezone.now)),
            ],
            options={
                "db_table": "audit_logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="LoginAttempt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254, db_index=True)),
                ("ip_address", models.GenericIPAddressField()),
                ("user_agent", models.TextField()),
                ("success", models.BooleanField(default=False)),
                ("failure_reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(db_index=True, default=timezone.now)),
            ],
            options={
                "db_table": "login_attempts",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="auditlog",
            name="user",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_logs", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["user", "-created_at"], name="audit_logs_user_created_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["action", "-created_at"], name="audit_logs_action_created_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["severity"], name="audit_logs_severity_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["resource_type", "resource_id"], name="audit_logs_resource_idx"),
        ),
        migrations.AddIndex(
            model_name="loginattempt",
            index=models.Index(fields=["email", "-created_at"], name="login_attempts_email_created_idx"),
        ),
        migrations.AddIndex(
            model_name="loginattempt",
            index=models.Index(fields=["ip_address", "-created_at"], name="login_attempts_ip_created_idx"),
        ),
    ]
