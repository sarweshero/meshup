"""REST views exposing realtime documentation metadata."""
from __future__ import annotations

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_yasg.utils import swagger_auto_schema

from .serializers import RealtimeMetadataResponseSerializer


class RealtimeMetadataView(APIView):
    """Provide metadata describing websocket endpoints and events."""

    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Realtime capabilities",
        responses={status.HTTP_200_OK: RealtimeMetadataResponseSerializer},
        tags=["Realtime"],
    )
    def get(self, request):
        base_ws_url = settings.SWAGGER_API_BASE_URL.replace("http", "ws") if getattr(settings, "SWAGGER_API_BASE_URL", "").startswith("http") else "wss://flowdrix.tech/api/v1"
        response_data = {
            "websocket_url": f"{base_ws_url.replace('/api/v1', '')}/ws/v1/realtime/servers/{{server_id}}/channels/{{channel_id}}/",
            "authentication": "JWT access token passed as ?token=... or Authorization: Bearer header",
            "events": [
                {
                    "key": "message.send",
                    "description": "Client -> server. Broadcasts a new message to channel subscribers.",
                },
                {
                    "key": "message.created",
                    "description": "Server -> client. Emitted when a new message is persisted (REST or websocket).",
                },
                {
                    "key": "typing.start",
                    "description": "Client -> server. Indicates the user started typing. Broadcast to channel members.",
                },
                {
                    "key": "typing.stop",
                    "description": "Client -> server. Indicates the user stopped typing. Broadcast to channel members.",
                },
                {
                    "key": "presence.join",
                    "description": "Server -> client. Published when a user joins the websocket channel.",
                },
                {
                    "key": "presence.leave",
                    "description": "Server -> client. Published when a user disconnects from the channel.",
                },
                {
                    "key": "presence.alive",
                    "description": "Server -> client. Heartbeat reply confirming the user is still connected.",
                },
            ],
        }
        return Response(response_data)
