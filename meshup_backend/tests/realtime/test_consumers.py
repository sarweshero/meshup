"""Integration tests for realtime websocket consumers."""
import asyncio

from asgiref.sync import sync_to_async
import pytest
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from config.asgi import application
from apps.channels.models import Channel
from apps.roles.models import ServerMember
from apps.servers.models import Server
from apps.users.models import User

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.asyncio
async def test_channel_websocket_message_flow(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

    user = await sync_to_async(User.objects.create_user)(
        email="socket@example.com", username="socket", password="strongpass123"
    )
    server = await sync_to_async(Server.objects.create)(name="Realtime", owner=user)
    channel = await sync_to_async(Channel.objects.create)(name="general", server=server, created_by=user)
    await sync_to_async(ServerMember.objects.create)(server=server, user=user, is_owner=True)

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    communicator = WebsocketCommunicator(
        application,
        f"/ws/v1/realtime/servers/{server.id}/channels/{channel.id}/?token={access_token}",
    )
    connected, _ = await communicator.connect()
    assert connected

    join_event = await asyncio.wait_for(communicator.receive_json_from(), timeout=2)
    assert join_event["event"] == "presence.join"

    await communicator.send_json_to({"event": "message.send", "payload": {"content": "Hello realtime"}})

    ack_event = await asyncio.wait_for(communicator.receive_json_from(), timeout=2)
    assert ack_event["event"] == "message.ack"
    assert ack_event["payload"]["content"] == "Hello realtime"

    broadcast_event = await asyncio.wait_for(communicator.receive_json_from(), timeout=2)
    assert broadcast_event["event"] == "message.created"
    assert broadcast_event["payload"]["content"] == "Hello realtime"

    await communicator.disconnect()

    channel_layer = get_channel_layer()
    assert channel_layer is not None
