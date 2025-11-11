"""Task management models for Meshup."""
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Task(models.Model):
    """Task model for team task management and assignment."""

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("overdue", "Overdue"),
        ("cancelled", "Cancelled"),
    )

    PRIORITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks"
    )
    assigned_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, related_name="created_tasks"
    )
    server = models.ForeignKey("servers.Server", on_delete=models.CASCADE, related_name="tasks")
    channel = models.ForeignKey(
        "meshup_channels.Channel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        help_text="Optional channel association",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium", db_index=True)
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Task completion percentage",
    )
    due_date = models.DateTimeField(null=True, blank=True, db_index=True)
    start_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True, help_text="List of tag strings")
    attachments = models.JSONField(default=list, blank=True, help_text="List of attachment URLs")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tasks"
        ordering = ["-priority", "due_date", "-created_at"]
        indexes = [
            models.Index(fields=["server", "status"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["due_date", "status"]),
            models.Index(fields=["-priority", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"

    def save(self, *args, **kwargs):
        if self.due_date and self.due_date < timezone.now() and self.status not in [
            "completed",
            "cancelled",
        ]:
            self.status = "overdue"
        if self.status == "completed" and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)


class TaskComment(models.Model):
    """Comment model for task discussions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="task_comments")
    content = models.TextField()
    reply_to = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies"
    )
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "task_comments"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["task", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Comment by {self.author.username} on {self.task.title}"


class TaskAttachment(models.Model):
    """Attachment model for task files and documents."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="task_attachments")
    file = models.FileField(upload_to="task_attachments/")
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    uploaded_by = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "task_attachments"

    def __str__(self) -> str:
        return self.file_name


class TaskAssignee(models.Model):
    """Model for multiple task assignees (for team tasks)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="assignees")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="task_assignments")
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "task_assignees"
        unique_together = [["task", "user"]]

    def __str__(self) -> str:
        return f"{self.user.username} assigned to {self.task.title}"
