from django.urls import path

from .consumers import ChannelChatConsumer

websocket_urlpatterns = [
    path(
        "ws/v1/realtime/servers/<uuid:server_id>/channels/<uuid:channel_id>/",
        ChannelChatConsumer.as_asgi(),
        name="realtime-channel",
    ),
]
