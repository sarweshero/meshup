"""URL configuration for message endpoints."""
from django.urls import path

from .views import DirectMessageViewSet, MessageViewSet

channel_messages = MessageViewSet.as_view({"get": "list", "post": "create"})
message_detail = MessageViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})
react = MessageViewSet.as_view({"post": "react"})
unreact = MessageViewSet.as_view({"delete": "unreact"})
pin = MessageViewSet.as_view({"post": "pin"})
unpin = MessageViewSet.as_view({"delete": "unpin"})

dm_list = DirectMessageViewSet.as_view({"get": "list", "post": "create"})
dm_detail = DirectMessageViewSet.as_view({"get": "retrieve", "delete": "destroy"})
dm_messages = DirectMessageViewSet.as_view({"get": "messages", "post": "messages"})

urlpatterns = [
    path("channels/<uuid:channel_id>/", channel_messages, name="channel-messages"),
    path("channels/<uuid:channel_id>/<uuid:pk>/", message_detail, name="message-detail"),
    path("channels/<uuid:channel_id>/<uuid:pk>/react/", react, name="message-react"),
    path("channels/<uuid:channel_id>/<uuid:pk>/unreact/", unreact, name="message-unreact"),
    path("channels/<uuid:channel_id>/<uuid:pk>/pin/", pin, name="message-pin"),
    path("channels/<uuid:channel_id>/<uuid:pk>/unpin/", unpin, name="message-unpin"),
    path("dm/", dm_list, name="dm-list"),
    path("dm/<uuid:pk>/", dm_detail, name="dm-detail"),
    path("dm/<uuid:pk>/messages/", dm_messages, name="dm-messages"),
]
