"""WebSocket consumer for real-time event updates."""
import json
import logging
from datetime import datetime

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class EventConsumer(AsyncWebsocketConsumer):
    """Consumer delivering live event RSVPs and updates."""

    async def connect(self):
        self.event_id = self.scope["url_route"]["kwargs"].get("event_id")
        self.user = self.scope.get("user")
        self.group_name = f"event_{self.event_id}"

        if not self.user or not self.user.is_authenticated or not self.event_id:
            await self.close(code=4001)
            return

        if not await self.verify_event_access():
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("%s connected to event %s", self.user.username, self.event_id)

    async def disconnect(self, close_code):
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error", "message": "Invalid JSON"}))
            return

        message_type = payload.get("type")
        data = payload.get("data", {})

        if message_type == "rsvp_update":
            await self.handle_rsvp_update(data)
        elif message_type == "event_update":
            await self.handle_event_update(data)

    async def handle_rsvp_update(self, data):
        rsvp_status = data.get("rsvp_status")
        notes = data.get("notes", "")

        if not rsvp_status:
            return

        if await self.update_rsvp(rsvp_status, notes):
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "rsvp_changed",
                    "user_id": str(self.user.id),
                    "username": self.user.username,
                    "status": rsvp_status,
                    "timestamp": datetime.now().isoformat(),
                },
            )

    async def handle_event_update(self, data):
        if not await self.verify_is_organizer():
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "message": "Only organiser can update event"}
                )
            )
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "event_modified",
                "event_id": self.event_id,
                "modified_by": self.user.username,
                "changes": data,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def rsvp_changed(self, event):
        payload = dict(event)
        payload["type"] = "rsvp_changed"
        await self.send(text_data=json.dumps(payload))

    async def event_modified(self, event):
        payload = dict(event)
        payload["type"] = "event_modified"
        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def verify_event_access(self):
        from apps.events.models import Event

        try:
            event = Event.objects.select_related("server").get(id=self.event_id)
            return event.server.members.filter(user=self.user).exists()
        except Event.DoesNotExist:
            return False

    @database_sync_to_async
    def update_rsvp(self, rsvp_status, notes):
        from django.utils import timezone

        from apps.events.models import Event, EventAttendee

        try:
            event = Event.objects.get(id=self.event_id)
            EventAttendee.objects.update_or_create(
                event=event,
                user=self.user,
                defaults={
                    "rsvp_status": rsvp_status,
                    "notes": notes,
                    "responded_at": timezone.now(),
                },
            )
            return True
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error updating RSVP: %s", exc)
            return False

    @database_sync_to_async
    def verify_is_organizer(self):
        from apps.events.models import Event

        try:
            event = Event.objects.select_related("created_by").get(id=self.event_id)
            return event.created_by_id == self.user.id
        except Event.DoesNotExist:
            return False
