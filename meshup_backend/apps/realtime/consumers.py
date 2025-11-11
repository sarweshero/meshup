"""Realtime websocket consumers for live messaging."""
from __future__ import annotations

from typing import Any, Dict, Optional

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from apps.channels.models import Channel
from apps.messages.models import Message
from apps.roles.models import ServerMember
from apps.users.models import User

from .utils import serialize_message_for_realtime, serialize_user_basic


@sync_to_async
def _get_channel(channel_id: str) -> Channel:
    return Channel.objects.select_related("server").get(id=channel_id)


@sync_to_async
def _user_is_member(server_id, user: User) -> bool:
    if getattr(user, "is_admin", False):
        return True
    if user.is_anonymous:
        return False
    return ServerMember.objects.filter(server_id=server_id, user=user, is_banned=False).exists()


@sync_to_async
def _create_message(*, channel: Channel, author: User, content: str, reply_to: Optional[str] = None) -> Message:
    kwargs: Dict[str, Any] = {
        "channel": channel,
        "author": author,
        "content": content,
    }
    if reply_to:
        kwargs["reply_to_id"] = reply_to
    return Message.objects.create(**kwargs)


class ChannelChatConsumer(AsyncJsonWebsocketConsumer):
    """Handle live messaging, typing indicators, and presence updates."""

    group_name: str
    channel: Channel

    async def connect(self) -> None:
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.server_id = str(self.scope["url_route"]["kwargs"]["server_id"])
        self.channel_id = str(self.scope["url_route"]["kwargs"]["channel_id"])
        try:
            self.channel = await _get_channel(self.channel_id)
        except Channel.DoesNotExist:
            await self.close(code=4404)
            return

        if str(self.channel.server_id) != self.server_id:
            await self.close(code=4403)
            return

        has_access = await _user_is_member(self.server_id, user) or self.channel.server.owner_id == user.id
        if not has_access:
            await self.close(code=4403)
            return

        self.group_name = f"realtime.channel.{self.channel_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._broadcast_presence(event="presence.join")

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self._broadcast_presence(event="presence.leave")

    async def receive_json(self, content: Dict[str, Any], *args, **kwargs):
        event = content.get("event")
        if not event:
            return

        if event == "message.send":
            await self._handle_message_send(content)
        elif event in {"typing.start", "typing.stop"}:
            await self._broadcast_typing(event)
        elif event == "presence.ping":
            await self._broadcast_presence(event="presence.alive")

    async def _handle_message_send(self, content: Dict[str, Any]):
        text = (content.get("payload") or {}).get("content", "").strip()
        reply_to = (content.get("payload") or {}).get("reply_to")
        if not text:
            await self.send_json({"event": "error", "detail": "Message content cannot be empty."})
            return

        user: User = self.scope["user"]
        message = await _create_message(channel=self.channel, author=user, content=text, reply_to=reply_to)
        payload = await sync_to_async(serialize_message_for_realtime)(message)
        await self.send_json({"event": "message.ack", "payload": payload})

    async def _broadcast_presence(self, *, event: str):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "realtime.broadcast",
                "event": event,
                "payload": {
                    "user": serialize_user_basic(self.scope["user"]),
                },
            },
        )

    async def _broadcast_typing(self, event: str):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "realtime.broadcast",
                "event": event,
                "payload": {
                    "user": serialize_user_basic(self.scope["user"]),
                },
            },
        )

    async def realtime_message(self, event: Dict[str, Any]):
        await self.send_json(event)

    async def realtime_broadcast(self, event: Dict[str, Any]):
        await self.send_json(event)
