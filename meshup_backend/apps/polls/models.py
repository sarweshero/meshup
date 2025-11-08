"""Poll models for Meshup surveys."""
import uuid

from django.db import models
from django.utils import timezone


class Poll(models.Model):
    """Poll model for team surveys and voting."""

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("active", "Active"),
        ("closed", "Closed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.CharField(max_length=500, db_index=True)
    description = models.TextField(blank=True)
    server = models.ForeignKey("servers.Server", on_delete=models.CASCADE, related_name="polls")
    channel = models.ForeignKey(
        "channels.Channel", on_delete=models.SET_NULL, null=True, blank=True, related_name="polls"
    )
    created_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, related_name="created_polls"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active", db_index=True)
    allow_multiple_votes = models.BooleanField(default=False)
    allow_add_options = models.BooleanField(default=False)
    anonymous_votes = models.BooleanField(default=False)
    show_results_before_vote = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    total_votes = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "polls"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["server", "status"]),
            models.Index(fields=["expires_at", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.question} ({self.status})"

    def save(self, *args, **kwargs):
        if self.expires_at and self.expires_at < timezone.now() and self.status == "active":
            self.status = "closed"
            self.closed_at = timezone.now()
        super().save(*args, **kwargs)

    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at < timezone.now())


class PollOption(models.Model):
    """Poll option model for vote choices."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    option_text = models.CharField(max_length=200)
    position = models.IntegerField(default=0)
    added_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="added_poll_options"
    )
    vote_count = models.IntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "poll_options"
        ordering = ["position", "created_at"]
        unique_together = [["poll", "option_text"]]

    def __str__(self) -> str:
        return f"{self.option_text} ({self.vote_count} votes)"

    def calculate_percentage(self) -> float:
        if self.poll.total_votes == 0:
            return 0
        return (self.vote_count / self.poll.total_votes) * 100


class PollVote(models.Model):
    """Poll vote model tracking individual votes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="poll_votes")
    voted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "poll_votes"
        indexes = [
            models.Index(fields=["poll", "user"]),
            models.Index(fields=["option"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} voted for {self.option.option_text}"


class PollComment(models.Model):
    """Comment model for poll discussions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="poll_comments")
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "poll_comments"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Comment by {self.author.username} on poll {self.poll.question}"
