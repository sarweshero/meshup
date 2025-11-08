"""Note models for Meshup."""
import uuid

from django.db import models
from django.utils import timezone


class Note(models.Model):
    """Note model for server-wide collaborative notes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, db_index=True)
    content = models.TextField()
    server = models.ForeignKey("servers.Server", on_delete=models.CASCADE, related_name="notes")
    created_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, related_name="created_notes"
    )
    version = models.IntegerField(default=1)
    last_edited_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, related_name="edited_notes"
    )
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False, help_text="Locked notes cannot be edited")
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notes"
        ordering = ["-is_pinned", "-updated_at"]
        indexes = [
            models.Index(fields=["server", "-updated_at"]),
            models.Index(fields=["server", "is_pinned"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} (v{self.version})"

    def save(self, *args, **kwargs):
        if self.pk:
            self.version += 1
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                update_set = set(update_fields)
                update_set.add("version")
                kwargs["update_fields"] = list(update_set)
        super().save(*args, **kwargs)


class NoteVersion(models.Model):
    """Version history model tracking all note edits."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="version_history")
    version_number = models.IntegerField()
    title = models.CharField(max_length=200)
    content = models.TextField()
    edited_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, related_name="note_edits"
    )
    change_description = models.TextField(blank=True, help_text="Description of changes made")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "note_versions"
        ordering = ["-version_number"]
        unique_together = [["note", "version_number"]]
        indexes = [
            models.Index(fields=["note", "-version_number"]),
        ]

    def __str__(self) -> str:
        return f"{self.note.title} - v{self.version_number}"


class NoteCollaborator(models.Model):
    """Model for tracking note collaborators with specific permissions."""

    PERMISSION_CHOICES = (
        ("view", "View Only"),
        ("edit", "Can Edit"),
        ("admin", "Full Admin"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="collaborators")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="note_collaborations")
    permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES, default="view")
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "note_collaborators"
        unique_together = [["note", "user"]]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.permission} on {self.note.title}"
