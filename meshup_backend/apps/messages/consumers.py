"""WebSocket consumers for real-time messaging."""
import json
import logging
from datetime import datetime

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class MessageConsumer(AsyncWebsocketConsumer):
    """Consumer managing channel-based real-time messaging."""

    async def connect(self):
        self.channel_id = self.scope["url_route"]["kwargs"].get("channel_id")
        self.user = self.scope.get("user")
        self.group_name = f"channel_{self.channel_id}"

        if not self.user or not self.user.is_authenticated or not self.channel_id:
            await self.close(code=4001)
            logger.warning("Unauthenticated or invalid channel connection attempt: %s", self.channel_id)
            return

        has_access = await self.verify_channel_access()
        if not has_access:
            await self.close(code=4003)
            logger.warning("User %s denied access to channel %s", self.user.username, self.channel_id)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.update_user_presence(True)
        await self.accept()

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user_joined",
                "user_id": str(self.user.id),
                "username": self.user.username,
                "avatar": self.user.avatar.url if self.user.avatar else None,
                "timestamp": datetime.now().isoformat(),
            },
        )

        logger.info("%s connected to channel %s", self.user.username, self.channel_id)

    async def disconnect(self, close_code):
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.update_user_presence(False)

            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "user_left",
                    "user_id": str(self.user.id),
                    "username": self.user.username,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        logger.info("%s disconnected from channel %s", self.user.username, self.channel_id)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps({"type": "error", "message": "Invalid JSON format"})
            )
            return

        message_type = payload.get("type")
        data = payload.get("data", {})

        try:
            if message_type == "message":
                await self.handle_message(data)
            elif message_type == "typing":
                await self.handle_typing(data)
            elif message_type == "reaction":
                await self.handle_reaction(data)
            elif message_type == "presence":
                await self.handle_presence(data)
            else:
                logger.warning("Unsupported websocket event type: %s", message_type)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Error handling websocket event: %s", exc)
            await self.send(
                text_data=json.dumps({"type": "error", "message": "Error processing message"})
            )

    async def handle_message(self, data):
        content = (data.get("content") or "").strip()
        reply_to_id = data.get("reply_to")
        thread_id = data.get("thread_id")

        if not content or len(content) > 4000:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Message must be between 1 and 4000 characters",
                    }
                )
            )
            return

        if await self.check_slowmode():
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "You are sending messages too quickly. Please wait.",
                    }
                )
            )
            return

        message = await self.save_message(content, reply_to_id, thread_id)
        if not message:
            await self.send(
                text_data=json.dumps({"type": "error", "message": "Failed to save message"})
            )
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat_message",
                "id": str(message["id"]),
                "channel_id": str(message["channel_id"]),
                "author_id": str(message["author_id"]),
                "author": message["author"],
                "avatar": message.get("avatar"),
                "content": message["content"],
                "reply_to": message.get("reply_to"),
                "thread_id": message.get("thread_id"),
                "created_at": message["created_at"],
                "edited": False,
            },
        )

    async def handle_typing(self, data):
        is_typing = bool(data.get("is_typing", False))
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user_typing",
                "user_id": str(self.user.id),
                "username": self.user.username,
                "is_typing": is_typing,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def handle_reaction(self, data):
        message_id = data.get("message_id")
        emoji = data.get("emoji")
        action = data.get("action", "add")

        if not message_id or not emoji:
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "message": "message_id and emoji are required"}
                )
            )
            return

        success = await self.save_reaction(message_id, emoji, action)
        if not success:
            await self.send(
                text_data=json.dumps({"type": "error", "message": "Failed to process reaction"})
            )
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "message_reaction",
                "message_id": message_id,
                "user_id": str(self.user.id),
                "username": self.user.username,
                "emoji": emoji,
                "action": action,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def handle_presence(self, data):
        status = data.get("status", "online")
        await self.update_user_status(status)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user_presence_update",
                "user_id": str(self.user.id),
                "username": self.user.username,
                "status": status,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def chat_message(self, event):
        payload = dict(event)
        payload["type"] = "message"
        await self.send(text_data=json.dumps(payload))

    async def user_typing(self, event):
        if event["user_id"] == str(self.user.id):
            return
        payload = dict(event)
        payload["type"] = "typing"
        await self.send(text_data=json.dumps(payload))

    async def user_joined(self, event):
        payload = dict(event)
        payload["type"] = "user_joined"
        await self.send(text_data=json.dumps(payload))

    async def user_left(self, event):
        payload = dict(event)
        payload["type"] = "user_left"
        await self.send(text_data=json.dumps(payload))

    async def message_reaction(self, event):
        payload = dict(event)
        payload["type"] = "reaction"
        await self.send(text_data=json.dumps(payload))

    async def user_presence_update(self, event):
        payload = dict(event)
        payload["type"] = "presence_update"
        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def verify_channel_access(self):
        from apps.channels.models import Channel
        from apps.roles.models import ServerMember

        try:
            channel = Channel.objects.select_related("server").get(id=self.channel_id)
            if not channel.is_private:
                return True
            return ServerMember.objects.filter(server=channel.server, user=self.user, is_banned=False).exists()
        except Channel.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content, reply_to_id=None, thread_id=None):
        from apps.channels.models import Channel
        from apps.messages.models import Message

        try:
            channel = Channel.objects.get(id=self.channel_id)
            message_kwargs = {
                "channel": channel,
                "author": self.user,
                "content": content,
            }
            if reply_to_id:
                message_kwargs["reply_to_id"] = reply_to_id
            if thread_id:
                message_kwargs["thread_id"] = thread_id

            message = Message.objects.create(**message_kwargs)
            return {
                "id": message.id,
                "channel_id": message.channel_id,
                "author_id": message.author_id,
                "author": message.author.username,
                "avatar": message.author.avatar.url if message.author.avatar else None,
                "content": message.content,
                "reply_to": str(message.reply_to_id) if message.reply_to_id else None,
                "thread_id": str(message.thread_id) if message.thread_id else None,
                "created_at": message.created_at.isoformat(),
            }
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error saving message: %s", exc)
            return None

    @database_sync_to_async
    def save_reaction(self, message_id, emoji, action):
        from apps.messages.models import Message, MessageReaction

        try:
            message = Message.objects.get(id=message_id)
            if action == "add":
                MessageReaction.objects.get_or_create(
                    message=message,
                    user=self.user,
                    emoji=emoji,
                )
            else:
                MessageReaction.objects.filter(message=message, user=self.user, emoji=emoji).delete()
            return True
        except Message.DoesNotExist:
            return False
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error updating reaction: %s", exc)
            return False

    @database_sync_to_async
    def check_slowmode(self):
        from apps.channels.models import Channel

        try:
            channel = Channel.objects.get(id=self.channel_id)
            if channel.slowmode_delay == 0:
                return False

            cache_key = f"slowmode:{self.channel_id}:{self.user.id}"
            last_message_time = cache.get(cache_key)
            if last_message_time is None:
                cache.set(cache_key, timezone.now().timestamp(), channel.slowmode_delay)
                return False
            return True
        except Channel.DoesNotExist:
            return False

    @database_sync_to_async
    def update_user_presence(self, is_online):
        cache_key = f"presence:{self.channel_id}:{self.user.id}"
        if is_online:
            cache.set(cache_key, True, timeout=3600)
        else:
            cache.delete(cache_key)

    @database_sync_to_async
    def update_user_status(self, status):
        from apps.users.models import User

        try:
            user = User.objects.get(id=self.user.id)
            user.status = status
            user.save(update_fields=["status", "updated_at"])
            return True
        except User.DoesNotExist:
            return False
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error updating user status: %s", exc)
            return False


class DirectMessageConsumer(AsyncWebsocketConsumer):
    """Consumer handling direct-message conversations."""

    async def connect(self):
        self.dm_channel_id = self.scope["url_route"]["kwargs"].get("dm_channel_id")
        self.user = self.scope.get("user")
        self.group_name = f"dm_{self.dm_channel_id}"

        if not self.user or not self.user.is_authenticated or not self.dm_channel_id:
            await self.close(code=4001)
            return

        if not await self.verify_dm_access():
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info("%s connected to DM %s", self.user.username, self.dm_channel_id)

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

        if payload.get("type") == "message":
            await self.handle_dm_message(payload.get("data", {}))

    async def handle_dm_message(self, data):
        content = (data.get("content") or "").strip()
        if not content:
            return

        message = await self.save_dm_message(content)
        if not message:
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "dm_message",
                "id": str(message["id"]),
                "author_id": str(message["author_id"]),
                "author": message["author"],
                "content": message["content"],
                "created_at": message["created_at"],
            },
        )

    async def dm_message(self, event):
        payload = dict(event)
        payload["type"] = "message"
        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def verify_dm_access(self):
        from apps.messages.models import DirectMessage

        try:
            dm_channel = DirectMessage.objects.prefetch_related("participants").get(id=self.dm_channel_id)
            return dm_channel.participants.filter(id=self.user.id).exists()
        except DirectMessage.DoesNotExist:
            return False

    @database_sync_to_async
    def save_dm_message(self, content):
        from apps.messages.models import DirectMessage, DirectMessageMessage

        try:
            dm_channel = DirectMessage.objects.get(id=self.dm_channel_id)
            message = DirectMessageMessage.objects.create(
                dm_channel=dm_channel,
                author=self.user,
                content=content,
            )
            return {
                "id": message.id,
                "author_id": message.author_id,
                "author": message.author.username,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error saving DM message: %s", exc)
            return None
