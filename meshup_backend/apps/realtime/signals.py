"""Signal handlers to broadcast realtime events via channel layer."""
from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.messages.models import Message

from .utils import serialize_message_for_realtime


@receiver(post_save, sender=Message)
def broadcast_message_created(sender, instance: Message, created: bool, **kwargs):
    """Broadcast message creation events to websocket subscribers."""

    if not created:
        return

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    payload = serialize_message_for_realtime(instance)
    async_to_sync(channel_layer.group_send)(
        f"realtime.channel.{instance.channel_id}",
        {
            "type": "realtime.message",
            "event": "message.created",
            "payload": payload,
        },
    )
