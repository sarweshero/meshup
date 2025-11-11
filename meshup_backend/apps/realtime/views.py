"""REST views exposing realtime documentation metadata."""
from __future__ import annotations

from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RealtimeMetadataResponseSerializer


class RealtimeMetadataView(APIView):
    """Provide metadata describing websocket endpoints and events."""

    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Realtime capabilities",
        operation_description=(
            "Developers can discover websocket connection details for live messaging, typing "
            "indicators, and presence updates. Use the documented `websocket_url` template and "
            "pass a valid JWT access token either as `?token=<access>` query parameter or in the "
            "`Authorization: Bearer <access>` header when initiating the websocket handshake."
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Realtime websocket metadata",
                schema=RealtimeMetadataResponseSerializer,
                examples={
                    "application/json": {
                        "websocket_url": "wss://flowdrix.tech/ws/v1/realtime/servers/{server_id}/channels/{channel_id}/",
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
                                "description": "Client -> server. Indicates the user started typing.",
                            },
                            {
                                "key": "typing.stop",
                                "description": "Client -> server. Indicates the user stopped typing.",
                            },
                            {
                                "key": "presence.join",
                                "description": "Server -> client. User joined the websocket channel.",
                            },
                            {
                                "key": "presence.leave",
                                "description": "Server -> client. User disconnected from the channel.",
                            },
                            {
                                "key": "presence.alive",
                                "description": "Server -> client. Heartbeat acknowledgement reply.",
                            },
                        ],
                        "direct_message_websocket_url": "wss://flowdrix.tech/ws/v1/realtime/direct-messages/{dm_id}/",
                        "direct_message_events": [
                            {
                                "key": "message.send",
                                "description": "Client -> server. Persists a DM and delivers to participants.",
                            },
                            {
                                "key": "message.created",
                                "description": "Server -> client. Emitted when a DM message is persisted.",
                            },
                            {
                                "key": "typing.start",
                                "description": "Client -> server. Indicates the user started typing in the DM.",
                            },
                            {
                                "key": "typing.stop",
                                "description": "Client -> server. Indicates the user stopped typing in the DM.",
                            },
                            {
                                "key": "presence.join",
                                "description": "Server -> client. Participant joined the DM websocket stream.",
                            },
                            {
                                "key": "presence.leave",
                                "description": "Server -> client. Participant disconnected from the DM stream.",
                            },
                            {
                                "key": "presence.alive",
                                "description": "Server -> client. Heartbeat reply for DM connections.",
                            },
                        ],
                    }
                },
            )
        },
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
            "direct_message_websocket_url": f"{base_ws_url.replace('/api/v1', '')}/ws/v1/realtime/direct-messages/{{dm_id}}/",
            "direct_message_events": [
                {
                    "key": "message.send",
                    "description": "Client -> server. Persists a direct message and broadcasts it to participants.",
                },
                {
                    "key": "message.created",
                    "description": "Server -> client. Published when a DM message is saved (REST or websocket).",
                },
                {
                    "key": "typing.start",
                    "description": "Client -> server. Indicates the user started typing in the DM conversation.",
                },
                {
                    "key": "typing.stop",
                    "description": "Client -> server. Indicates the user stopped typing in the DM conversation.",
                },
                {
                    "key": "presence.join",
                    "description": "Server -> client. Participant joined the DM websocket stream.",
                },
                {
                    "key": "presence.leave",
                    "description": "Server -> client. Participant disconnected from the DM stream.",
                },
                {
                    "key": "presence.alive",
                    "description": "Server -> client. DM heartbeat reply confirming the participant is still connected.",
                },
            ],
        }
        return Response(response_data)
