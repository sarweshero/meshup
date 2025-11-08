"""Event API views."""
from datetime import datetime, timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.servers.models import Server
from apps.roles.models import ServerMember

from .models import Event, EventAttendee
from .serializers import EventAttendeeSerializer, EventCreateUpdateSerializer, EventSerializer


class EventViewSet(viewsets.ModelViewSet):
    """ViewSet for managing events and calendar."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["event_type", "status", "created_by"]
    search_fields = ["title", "description", "location", "tags"]
    ordering_fields = ["start_time", "end_time", "created_at"]
    ordering = ["start_time"]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return EventCreateUpdateSerializer
        return EventSerializer

    def get_queryset(self):
        server_id = self.kwargs.get("server_id")
        server = get_object_or_404(Server, id=server_id)
        if not ServerMember.objects.filter(
            server=server, user=self.request.user, is_banned=False
        ).exists() and server.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You do not have access to this server's events.")
        queryset = Event.objects.filter(server=server, is_deleted=False).select_related(
            "created_by", "server"
        ).prefetch_related("event_attendees")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            parsed_start = parse_datetime(start_date)
            if parsed_start:
                if timezone.is_naive(parsed_start):
                    parsed_start = timezone.make_aware(parsed_start, timezone.get_current_timezone())
                queryset = queryset.filter(start_time__gte=parsed_start)
        if end_date:
            parsed_end = parse_datetime(end_date)
            if parsed_end:
                if timezone.is_naive(parsed_end):
                    parsed_end = timezone.make_aware(parsed_end, timezone.get_current_timezone())
                queryset = queryset.filter(end_time__lte=parsed_end)
        return queryset

    def perform_create(self, serializer):
        server_id = self.kwargs.get("server_id")
        server = get_object_or_404(Server, id=server_id)
        if not ServerMember.objects.filter(
            server=server, user=self.request.user, is_banned=False
        ).exists() and server.owner != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied("You do not have permission to create events for this server.")
        return serializer.save(server=server, created_by=self.request.user)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["is_deleted", "deleted_at"])

    @action(detail=True, methods=["post"])
    def rsvp(self, request, server_id=None, pk=None):
        event = self.get_object()
        rsvp_status = request.data.get("rsvp_status")
        notes = request.data.get("notes", "")
        if not rsvp_status:
            return Response({"error": "rsvp_status is required"}, status=status.HTTP_400_BAD_REQUEST)
        attendee, _created = EventAttendee.objects.update_or_create(
            event=event,
            user=request.user,
            defaults={
                "rsvp_status": rsvp_status,
                "notes": notes,
                "responded_at": timezone.now(),
            },
        )
        serializer = EventAttendeeSerializer(attendee)
        return Response({"message": "RSVP updated successfully", "attendee": serializer.data})

    @action(detail=False, methods=["get"])
    def calendar(self, request, server_id=None):
        month = int(request.query_params.get("month", timezone.now().month))
        year = int(request.query_params.get("year", timezone.now().year))
        current_tz = timezone.get_current_timezone()
        start_date = timezone.make_aware(datetime(year, month, 1), current_tz)
        end_month = 1 if month == 12 else month + 1
        end_year = year + 1 if month == 12 else year
        end_date = timezone.make_aware(datetime(end_year, end_month, 1), current_tz)
        events = self.get_queryset().filter(start_time__gte=start_date, start_time__lt=end_date)
        serializer = self.get_serializer(events, many=True)
        return Response({"month": month, "year": year, "events": serializer.data})

    @action(detail=False, methods=["get"])
    def upcoming(self, request, server_id=None):
        now = timezone.now()
        week_later = now + timedelta(days=7)
        events = self.get_queryset().filter(start_time__gte=now, start_time__lte=week_later, status="scheduled")
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = self.perform_create(serializer)
        output = EventSerializer(event, context={"request": request})
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)
