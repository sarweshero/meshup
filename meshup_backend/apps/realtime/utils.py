"""Utility helpers for realtime features."""
from __future__ import annotations

import json
from typing import Any, Dict

from django.contrib.auth import get_user_model

from apps.messages.models import Message
from apps.messages.serializers import MessageSerializer
from apps.users.serializers import UserBasicSerializer

User = get_user_model()


def serialize_user_basic(user) -> Dict[str, Any]:
    """Serialize user info for realtime payloads."""

    return UserBasicSerializer(user).data


def serialize_message_for_realtime(message: Message) -> Dict[str, Any]:
    """Serialize message model using existing serializer with minimal context."""

    serializer = MessageSerializer(message, context={"request": None})
    data = serializer.data
    # Ensure payload is JSON-serializable (convert UUIDs, datetimes, etc. to strings)
    return json.loads(json.dumps(data, default=str))
