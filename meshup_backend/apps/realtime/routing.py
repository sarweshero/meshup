from django.urls import path

from .consumers import ChannelChatConsumer, DirectMessageConsumer

websocket_urlpatterns = [
    path(
        "ws/v1/realtime/servers/<uuid:server_id>/channels/<uuid:channel_id>/",
        ChannelChatConsumer.as_asgi(),
        name="realtime-channel",
    ),
    path(
        "ws/v1/realtime/direct-messages/<uuid:dm_id>/",
        DirectMessageConsumer.as_asgi(),
        name="realtime-direct-message",
    ),
]
