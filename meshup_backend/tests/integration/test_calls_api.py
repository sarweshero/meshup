"""Integration tests for call API endpoints."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.calls.models import CallInvitation, CallParticipant, CallSession
from apps.channels.models import Channel
from apps.roles.models import ServerMember
from apps.servers.models import Server

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def initiator(db):
    User = get_user_model()
    return User.objects.create_user(
        email="initiator@example.com",
        username="initiator",
        password="MeshupPass123!",
    )


@pytest.fixture
def recipient(db):
    User = get_user_model()
    return User.objects.create_user(
        email="recipient@example.com",
        username="recipient",
        password="MeshupPass123!",
    )


@pytest.fixture
def server(initiator, recipient):
    server = Server.objects.create(name="Test Server", owner=initiator)
    ServerMember.objects.create(server=server, user=initiator, is_owner=True)
    ServerMember.objects.create(server=server, user=recipient)
    return server


@pytest.fixture
def voice_channel(server, initiator):
    return Channel.objects.create(
        server=server,
        name="voice-room",
        channel_type="voice",
        created_by=initiator,
    )


def test_call_initiate_creates_session(api_client, initiator, recipient, server, voice_channel):
    api_client.force_authenticate(user=initiator)

    payload = {
        "call_type": "video",
        "recipients": [str(recipient.id)],
        "channel_id": str(voice_channel.id),
        "video_quality": "high",
        "enable_recording": False,
    }

    response = api_client.post("/api/v1/calls/initiate/", payload, format="json")
    assert response.status_code == 201

    call = CallSession.objects.get(id=response.data["id"])
    assert call.status == "ringing"
    assert call.channel == voice_channel
    assert call.participants.count() == 1  # only initiator is enrolled
    assert CallInvitation.objects.filter(call=call, recipient=recipient, status="pending").exists()


def test_call_join_leave_and_end_flow(api_client, initiator, recipient, server, voice_channel):
    api_client.force_authenticate(user=initiator)
    create_response = api_client.post(
        "/api/v1/calls/initiate/",
        {
            "call_type": "voice",
            "recipients": [str(recipient.id)],
            "channel_id": str(voice_channel.id),
        },
        format="json",
    )
    assert create_response.status_code == 201
    call_id = create_response.data["id"]

    join_client = APIClient()
    join_client.force_authenticate(user=recipient)
    join_response = join_client.post(f"/api/v1/calls/{call_id}/join/")
    assert join_response.status_code == 200
    assert join_response.data["message"] in {"Already in call", "Joined call successfully"}

    call = CallSession.objects.get(id=call_id)
    call.refresh_from_db()
    assert call.status == "active"
    assert call.participants.filter(user=recipient, left_at__isnull=True).count() == 1
    invitation = CallInvitation.objects.get(call=call, recipient=recipient)
    assert invitation.status == "accepted"

    leave_response = join_client.post(f"/api/v1/calls/{call_id}/leave/")
    assert leave_response.status_code == 200
    participant = CallParticipant.objects.get(call=call, user=recipient)
    assert participant.left_at is not None
    previous_peer_id = participant.peer_id

    rejoin_response = join_client.post(f"/api/v1/calls/{call_id}/join/")
    assert rejoin_response.status_code == 200
    rejoined_participant = CallParticipant.objects.get(call=call, user=recipient)
    assert rejoined_participant.left_at is None
    assert rejoined_participant.peer_id != previous_peer_id

    end_response = api_client.post(f"/api/v1/calls/{call_id}/end/")
    assert end_response.status_code == 200
    call.refresh_from_db()
    assert call.status == "ended"
    assert call.ended_at is not None

    post_end_join = join_client.post(f"/api/v1/calls/{call_id}/join/")
    assert post_end_join.status_code == 400
    assert post_end_join.data["error"] == "Call is no longer active"


def test_call_update_media_state(api_client, initiator, recipient, server, voice_channel):
    api_client.force_authenticate(user=initiator)
    create_response = api_client.post(
        "/api/v1/calls/initiate/",
        {
            "call_type": "video",
            "recipients": [str(recipient.id)],
            "channel_id": str(voice_channel.id),
        },
        format="json",
    )
    call_id = create_response.data["id"]

    join_client = APIClient()
    join_client.force_authenticate(user=initiator)
    join_client.post(f"/api/v1/calls/{call_id}/join/")

    media_response = api_client.post(
        f"/api/v1/calls/{call_id}/update_media/",
        {
            "audio_state": "muted",
            "video_state": "off",
        },
        format="json",
    )
    assert media_response.status_code == 200
    participant = CallParticipant.objects.get(call_id=call_id, user=initiator)
    assert participant.audio_state == "muted"
    assert participant.video_state == "off"
