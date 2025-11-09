"""WebSocket consumer for real-time call collaboration."""

from __future__ import annotations

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

logger = logging.getLogger(__name__)


class CallConsumer(AsyncWebsocketConsumer):
    """Consumer handling WebRTC signalling and call state updates."""

    async def connect(self):
        self.call_id = self.scope["url_route"]["kwargs"].get("call_id")
        self.user = self.scope.get("user")
        self.group_name = f"call_{self.call_id}"

        if not self.user or not self.user.is_authenticated or not self.call_id:
            await self.close(code=4001)
            return

        call_context = await self.get_call_context()
        if not call_context:
            await self.close(code=4003)
            return

        self.call_context = call_context

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info("User %s connected to call %s", self.user.username, self.call_id)

    async def disconnect(self, close_code):
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        username = getattr(self.user, "username", "anonymous")
        logger.info("User %s disconnected from call %s", username, self.call_id)

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

        try:
            if message_type == "signal":
                await self.handle_signal(data)
            elif message_type == "ice_candidate":
                await self.handle_ice_candidate(data)
            elif message_type == "heartbeat":
                await self.send(
                    text_data=json.dumps({"type": "heartbeat", "timestamp": timezone.now().isoformat()})
                )
            else:
                logger.debug("Unsupported call websocket message type: %s", message_type)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Error handling call websocket payload: %s", exc)
            await self.send(text_data=json.dumps({"type": "error", "message": "Error processing message"}))

    async def handle_signal(self, data):
        if not data:
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "call_signal",
                "from_user": str(self.user.id),
                "peer_id": data.get("peer_id"),
                "target_peer_id": data.get("target_peer_id"),
                "signal": data.get("signal"),
                "timestamp": timezone.now().isoformat(),
            },
        )

    async def handle_ice_candidate(self, data):
        if not data:
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "call_ice_candidate",
                "from_user": str(self.user.id),
                "peer_id": data.get("peer_id"),
                "candidate": data.get("candidate"),
                "sdp_mid": data.get("sdp_mid"),
                "sdp_mline_index": data.get("sdp_mline_index"),
                "timestamp": timezone.now().isoformat(),
            },
        )

    async def call_signal(self, event):
        if event.get("from_user") == str(self.user.id):
            return
        payload = dict(event)
        payload["type"] = "signal"
        await self.send(text_data=json.dumps(payload))

    async def call_ice_candidate(self, event):
        if event.get("from_user") == str(self.user.id):
            return
        payload = dict(event)
        payload["type"] = "ice_candidate"
        await self.send(text_data=json.dumps(payload))

    async def call_participant_joined(self, event):
        await self.send(text_data=json.dumps({
            "type": "participant_joined",
            "call_id": event.get("call_id"),
            "participant": event.get("participant"),
        }))

    async def call_participant_left(self, event):
        await self.send(text_data=json.dumps({
            "type": "participant_left",
            "call_id": event.get("call_id"),
            "participant": event.get("participant"),
        }))

    async def call_media_state(self, event):
        await self.send(text_data=json.dumps({
            "type": "media_state",
            "call_id": event.get("call_id"),
            "participant": event.get("participant"),
        }))

    async def call_screen_share_started(self, event):
        await self.send(text_data=json.dumps({
            "type": "screen_share_started",
            "call_id": event.get("call_id"),
            "screen_share": event.get("screen_share"),
        }))

    async def call_screen_share_ended(self, event):
        await self.send(text_data=json.dumps({
            "type": "screen_share_ended",
            "call_id": event.get("call_id"),
            "screen_share": event.get("screen_share"),
        }))

    async def call_recording_started(self, event):
        await self.send(text_data=json.dumps({
            "type": "recording_started",
            "call_id": event.get("call_id"),
            "recording": event.get("recording"),
        }))

    async def call_ended(self, event):
        await self.send(text_data=json.dumps({
            "type": "call_ended",
            "call_id": event.get("call_id"),
            "status": event.get("status"),
            "ended_at": event.get("ended_at"),
            "duration_seconds": event.get("duration_seconds"),
        }))

    @database_sync_to_async
    def get_call_context(self):
        from apps.calls.models import CallSession

        try:
            call = CallSession.objects.select_related("server").get(id=self.call_id)
        except CallSession.DoesNotExist:
            return None

        if call.participants.filter(user=self.user).exists():
            return {
                "call_id": str(call.id),
                "server_id": str(call.server_id) if call.server_id else None,
            }

        if call.server_id and call.server.members.filter(user=self.user).exists():
            return {
                "call_id": str(call.id),
                "server_id": str(call.server_id),
            }

        return None
