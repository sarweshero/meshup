"""Integration tests covering WebSocket consumers."""
from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta

import pytest
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from apps.calls.models import CallParticipant, CallSession
from apps.channels.models import Channel
from apps.events.models import Event
from apps.messages.models import DirectMessage
from apps.roles.models import ServerMember
from apps.servers.models import Server
from config.asgi import websocket_urlpatterns


pytestmark = pytest.mark.django_db(transaction=True)
@pytest.fixture
def websocket_app():
	return URLRouter(websocket_urlpatterns)



TEST_CHANNEL_LAYERS = {
	"default": {
		"BACKEND": "channels.layers.InMemoryChannelLayer",
	}
}


@pytest.fixture
def user(db):
	User = get_user_model()
	return User.objects.create_user(
		email="ws_test@meshup.test",
		username="ws_tester",
		password="Meshup!test123",
	)


@pytest.fixture
def another_user(db):
	User = get_user_model()
	return User.objects.create_user(
		email="ws_test_two@meshup.test",
		username="ws_tester_two",
		password="Meshup!test123",
	)


@pytest.fixture
def server(user):
	server = Server.objects.create(
		name="WebSocket Test Server",
		description="Server for websocket consumer tests",
		owner=user,
	)
	ServerMember.objects.create(server=server, user=user, is_owner=True)
	return server


@pytest.fixture
def server_with_two_members(server, another_user):
	ServerMember.objects.create(server=server, user=another_user, is_owner=False)
	return server


@pytest.fixture
def channel(server, user):
	return Channel.objects.create(
		server=server,
		name="ws-general",
		description="Channel used for websocket coverage",
		created_by=user,
	)


@pytest.fixture
def dm_channel(user):
	dm = DirectMessage.objects.create()
	dm.participants.add(user)
	return dm


@pytest.fixture
def call_session(server_with_two_members, user, another_user):
	call = CallSession.objects.create(
		call_type="video",
		status="active",
		initiator=user,
		server=server_with_two_members,
		call_token=f"token_{uuid.uuid4().hex}",
		room_id=f"room_{uuid.uuid4().hex}",
		started_at=timezone.now(),
		total_participants=2,
	)
	CallParticipant.objects.create(
		call=call,
		user=user,
		peer_id=f"peer_{uuid.uuid4().hex}",
	)
	CallParticipant.objects.create(
		call=call,
		user=another_user,
		peer_id=f"peer_{uuid.uuid4().hex}",
	)
	return call


@pytest.fixture
def event(server, channel, user):
	start = timezone.now() + timedelta(hours=1)
	end = start + timedelta(hours=1)
	return Event.objects.create(
		title="WebSocket Event",
		description="Event used for websocket consumer tests",
		server=server,
		channel=channel,
		created_by=user,
		start_time=start,
		end_time=end,
	)


@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
async def test_message_consumer_broadcasts(websocket_app, channel, user):
	communicator = WebsocketCommunicator(websocket_app, f"/ws/channels/{channel.id}/")
	communicator.scope["user"] = user
	connected, _ = await asyncio.wait_for(communicator.connect(), timeout=1)
	print("connected", connected)
	assert connected

	join_payload = await asyncio.wait_for(communicator.receive_json_from(), timeout=1)
	assert join_payload["type"] == "user_joined"

	await communicator.send_json_to({"type": "message", "data": {"content": "Hello WebSocket"}})
	message_payload = await asyncio.wait_for(communicator.receive_json_from(), timeout=1)
	assert message_payload["type"] == "message"
	assert message_payload["content"] == "Hello WebSocket"

	await communicator.disconnect()


@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
async def test_direct_message_consumer(websocket_app, dm_channel, user):
	communicator = WebsocketCommunicator(websocket_app, f"/ws/dm/{dm_channel.id}/")
	communicator.scope["user"] = user
	connected, _ = await asyncio.wait_for(communicator.connect(), timeout=1)
	assert connected

	await communicator.send_json_to({"type": "message", "data": {"content": "Ping"}})
	message_payload = await asyncio.wait_for(communicator.receive_json_from(), timeout=1)
	assert message_payload["type"] == "message"
	assert message_payload["content"] == "Ping"

	await communicator.disconnect()


@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
async def test_event_consumer_rsvp(websocket_app, event, user):
	communicator = WebsocketCommunicator(websocket_app, f"/ws/events/{event.id}/")
	communicator.scope["user"] = user
	connected, _ = await asyncio.wait_for(communicator.connect(), timeout=1)
	assert connected

	await communicator.send_json_to({"type": "rsvp_update", "data": {"rsvp_status": "attending", "notes": "On my way"}})
	payload = await asyncio.wait_for(communicator.receive_json_from(), timeout=1)
	assert payload["type"] == "rsvp_changed"
	assert payload["status"] == "attending"

	await communicator.disconnect()


@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
async def test_presence_consumer_status_updates(websocket_app, server, user):
	communicator = WebsocketCommunicator(websocket_app, f"/ws/presence/{server.id}/")
	communicator.scope["user"] = user
	connected, _ = await asyncio.wait_for(communicator.connect(), timeout=1)
	assert connected

	online_payload = await asyncio.wait_for(communicator.receive_json_from(), timeout=1)
	assert online_payload["type"] == "user_online"

	await communicator.send_json_to({"type": "status_update", "status": "away"})
	status_payload = await asyncio.wait_for(communicator.receive_json_from(), timeout=1)
	assert status_payload["type"] == "status_updated"
	assert status_payload["status"] == "away"

	await communicator.disconnect()


@pytest.mark.asyncio
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
async def test_call_consumer_signal_and_broadcast(websocket_app, call_session, user, another_user):
	communicator_one = WebsocketCommunicator(websocket_app, f"/ws/calls/{call_session.id}/")
	communicator_one.scope["user"] = user
	connected_one, _ = await asyncio.wait_for(communicator_one.connect(), timeout=1)
	assert connected_one

	communicator_two = WebsocketCommunicator(websocket_app, f"/ws/calls/{call_session.id}/")
	communicator_two.scope["user"] = another_user
	connected_two, _ = await asyncio.wait_for(communicator_two.connect(), timeout=1)
	assert connected_two

	await communicator_one.send_json_to(
		{
			"type": "signal",
			"data": {
				"peer_id": "peer_A",
				"target_peer_id": "peer_B",
				"signal": {"sdp": "offer"},
			},
		}
	)

	peer_payload = await asyncio.wait_for(communicator_two.receive_json_from(), timeout=1)
	assert peer_payload["type"] == "signal"
	assert peer_payload["peer_id"] == "peer_A"
	assert peer_payload["target_peer_id"] == "peer_B"

	await communicator_two.send_json_to(
		{
			"type": "ice_candidate",
			"data": {
				"peer_id": "peer_B",
				"candidate": {"candidate": "cand"},
				"sdp_mid": "0",
				"sdp_mline_index": 0,
			},
		}
	)

	ice_payload = await asyncio.wait_for(communicator_one.receive_json_from(), timeout=1)
	assert ice_payload["type"] == "ice_candidate"
	assert ice_payload["peer_id"] == "peer_B"

	channel_layer = get_channel_layer()
	await channel_layer.group_send(
		f"call_{call_session.id}",
		{
			"type": "call_participant_joined",
			"call_id": str(call_session.id),
			"participant": {"id": "abc"},
		}
	)

	joined_event = await asyncio.wait_for(communicator_one.receive_json_from(), timeout=1)
	assert joined_event["type"] == "participant_joined"
	assert joined_event["call_id"] == str(call_session.id)

	joined_event_two = await asyncio.wait_for(communicator_two.receive_json_from(), timeout=1)
	assert joined_event_two["type"] == "participant_joined"
	assert joined_event_two["call_id"] == str(call_session.id)

	await channel_layer.group_send(
		f"call_{call_session.id}",
		{
			"type": "call_ended",
			"call_id": str(call_session.id),
			"status": "ended",
			"ended_at": timezone.now().isoformat(),
			"duration_seconds": 12,
		}
	)

	ended_event = await asyncio.wait_for(communicator_two.receive_json_from(), timeout=1)
	assert ended_event["type"] == "call_ended"
	assert ended_event["duration_seconds"] == 12

	await communicator_one.disconnect()
	await communicator_two.disconnect()