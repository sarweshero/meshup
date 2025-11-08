"""Serializers for event scheduling."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users.serializers import UserBasicSerializer
from apps.roles.models import ServerMember

from .models import Event, EventAttendee


class EventAttendeeSerializer(serializers.ModelSerializer):
    """Serializer for event attendees."""

    user = UserBasicSerializer(read_only=True)

    class Meta:
        model = EventAttendee
        fields = (
            "id",
            "user",
            "rsvp_status",
            "is_organizer",
            "is_required",
            "notes",
            "responded_at",
            "invited_at",
        )
        read_only_fields = ("id", "invited_at")


class EventSerializer(serializers.ModelSerializer):
    """Complete serializer for events."""

    created_by = UserBasicSerializer(read_only=True)
    attendees_data = EventAttendeeSerializer(source="event_attendees", many=True, read_only=True)
    attendee_count = serializers.SerializerMethodField()
    attending_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = (
            "id",
            "title",
            "description",
            "server",
            "channel",
            "created_by",
            "event_type",
            "status",
            "start_time",
            "end_time",
            "all_day",
            "location",
            "meeting_link",
            "recurrence_type",
            "recurrence_end_date",
            "recurrence_interval",
            "attendees_data",
            "attendee_count",
            "attending_count",
            "reminder_minutes_before",
            "tags",
            "color",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def get_attendee_count(self, obj):
        return obj.event_attendees.count()

    def get_attending_count(self, obj):
        return obj.event_attendees.filter(rsvp_status="attending").count()


class EventCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating events."""

    attendee_ids = serializers.ListField(child=serializers.UUIDField(), write_only=True, required=False)

    class Meta:
        model = Event
        fields = (
            "title",
            "description",
            "channel",
            "event_type",
            "status",
            "start_time",
            "end_time",
            "all_day",
            "location",
            "meeting_link",
            "recurrence_type",
            "recurrence_end_date",
            "recurrence_interval",
            "attendee_ids",
            "reminder_minutes_before",
            "tags",
            "color",
        )

    def validate(self, attrs):
        if attrs.get("end_time") and attrs.get("start_time"):
            if attrs["end_time"] <= attrs["start_time"]:
                raise serializers.ValidationError({"end_time": "End time must be after start time"})
        recurrence_type = attrs.get("recurrence_type") or "none"
        if recurrence_type != "none" and not attrs.get("recurrence_end_date"):
            raise serializers.ValidationError({"recurrence_end_date": "Recurring events must have an end date"})
        return attrs

    def create(self, validated_data):
        attendee_ids = validated_data.pop("attendee_ids", [])
        attendee_ids = list({str(attendee_id) for attendee_id in attendee_ids})
        event = Event.objects.create(**validated_data)
        User = get_user_model()
        for user in User.objects.filter(id__in=attendee_ids):
            if not ServerMember.objects.filter(
                server=event.server, user=user, is_banned=False
            ).exists():
                continue
            EventAttendee.objects.create(
                event=event,
                user=user,
                is_organizer=(user == validated_data.get("created_by")),
            )
        if event.created_by:
            EventAttendee.objects.update_or_create(
                event=event,
                user=event.created_by,
                defaults={"is_organizer": True},
            )
        return event

    def update(self, instance, validated_data):
        attendee_ids = validated_data.pop("attendee_ids", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if attendee_ids is not None:
            attendee_ids = list({str(attendee_id) for attendee_id in attendee_ids})
            User = get_user_model()
            new_attendees = User.objects.filter(id__in=attendee_ids)

            accepted_ids = set()
            for user in new_attendees:
                if not ServerMember.objects.filter(
                    server=instance.server, user=user, is_banned=False
                ).exists():
                    continue
                EventAttendee.objects.update_or_create(
                    event=instance,
                    user=user,
                    defaults={
                        "is_organizer": bool(instance.created_by_id and user.id == instance.created_by_id),
                    },
                )
                accepted_ids.add(str(user.id))
            if instance.created_by:
                EventAttendee.objects.update_or_create(
                    event=instance,
                    user=instance.created_by,
                    defaults={"is_organizer": True},
                )
                accepted_ids.add(str(instance.created_by_id))

            # Remove attendees no longer present
            EventAttendee.objects.filter(event=instance).exclude(user_id__in=accepted_ids).delete()
        return instance
