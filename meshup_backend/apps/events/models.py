"""Event scheduling models for Meshup."""
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Event(models.Model):
    """Event model for scheduling team meetings and events."""

    EVENT_TYPES = (
        ("meeting", "Meeting"),
        ("deadline", "Deadline"),
        ("announcement", "Announcement"),
        ("milestone", "Milestone"),
        ("reminder", "Reminder"),
        ("other", "Other"),
    )

    STATUS_CHOICES = (
        ("scheduled", "Scheduled"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("postponed", "Postponed"),
    )

    RECURRENCE_TYPES = (
        ("none", "No Recurrence"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
        ("custom", "Custom"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    server = models.ForeignKey("servers.Server", on_delete=models.CASCADE, related_name="events")
    channel = models.ForeignKey(
        "meshup_channels.Channel", on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    created_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, related_name="created_events"
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default="meeting")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled", db_index=True)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=255, blank=True)
    meeting_link = models.URLField(blank=True, help_text="Virtual meeting link")
    recurrence_type = models.CharField(max_length=20, choices=RECURRENCE_TYPES, default="none")
    recurrence_end_date = models.DateTimeField(null=True, blank=True)
    recurrence_interval = models.IntegerField(default=1, help_text="Interval for recurrence (e.g., every 2 weeks)")
    parent_event = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="recurring_instances"
    )
    attendees = models.ManyToManyField(
        "users.User", through="EventAttendee", related_name="events_attending"
    )
    reminder_minutes_before = models.JSONField(
        default=list, help_text="List of minutes before event to send reminders [15, 60, 1440]"
    )
    tags = models.JSONField(default=list, blank=True)
    color = models.CharField(max_length=7, default="#3498db", help_text="Hex color for calendar display")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "events"
        ordering = ["start_time"]
        indexes = [
            models.Index(fields=["server", "start_time"]),
            models.Index(fields=["start_time", "end_time"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time")
        if self.recurrence_type != "none" and not self.recurrence_end_date:
            raise ValidationError("Recurring events must have an end date")


class EventAttendee(models.Model):
    """Model tracking event attendees and their RSVP status."""

    RSVP_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("attending", "Attending"),
        ("not_attending", "Not Attending"),
        ("maybe", "Maybe"),
        ("tentative", "Tentative"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="event_attendees")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="event_attendance")
    rsvp_status = models.CharField(max_length=20, choices=RSVP_STATUS_CHOICES, default="pending")
    is_organizer = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False, help_text="Required attendee vs optional")
    responded_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Attendee notes or comments")
    invited_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "event_attendees"
        unique_together = [["event", "user"]]
        indexes = [
            models.Index(fields=["event", "rsvp_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.rsvp_status} ({self.event.title})"


class EventReminder(models.Model):
    """Model for tracking sent event reminders."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="reminders")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="event_reminders")
    minutes_before = models.IntegerField()
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "event_reminders"
        unique_together = [["event", "user", "minutes_before"]]

    def __str__(self) -> str:
        return f"Reminder for {self.user.username} - {self.event.title}"
