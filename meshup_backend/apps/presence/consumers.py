"""WebSocket consumer for user presence tracking."""
import json
import logging
from datetime import datetime

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache

logger = logging.getLogger(__name__)


class PresenceConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for tracking per-server user presence."""

    async def connect(self):
        """Handle initial WebSocket connection for presence updates."""

        self.server_id = self.scope["url_route"]["kwargs"].get("server_id")
        self.user = self.scope.get("user")
        self.group_name = f"presence_{self.server_id}"

        if not self.user or not self.user.is_authenticated or not self.server_id:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.update_presence_cache(True)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user_online",
                "user_id": str(self.user.id),
                "username": self.user.username,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection for presence updates."""

        if getattr(self, "group_name", None):
            await self.update_presence_cache(False)

            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "user_offline",
                    "user_id": str(self.user.id),
                    "username": self.user.username,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """Process incoming presence payloads."""

        if not text_data:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            logger.warning("PresenceConsumer received invalid JSON payload")
            return

        if payload.get("type") == "status_update":
            status = payload.get("status")
            if status in {"online", "away", "dnd", "offline"}:
                await self.update_user_status(status)
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "status_updated",
                        "user_id": str(self.user.id),
                        "username": self.user.username,
                        "status": status,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

    async def user_online(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_online",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def user_offline(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_offline",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def status_updated(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "status_updated",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "status": event["status"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    @database_sync_to_async
    def update_presence_cache(self, is_online):
        cache_key = f"presence:{self.server_id}:{self.user.id}"
        if is_online:
            cache.set(cache_key, "online", timeout=3600)
        else:
            cache.delete(cache_key)

    @database_sync_to_async
    def update_user_status(self, status):
        from apps.users.models import User

        try:
            user = User.objects.get(id=self.user.id)
            user.status = status
            user.save(update_fields=["status", "updated_at"])
        except User.DoesNotExist:
            logger.warning("Attempted to update status for non-existent user %s", self.user.id)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error updating presence status: %s", exc)
