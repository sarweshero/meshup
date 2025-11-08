"""URL configuration for channel endpoints."""
from django.urls import path

from .views import ChannelViewSet

list_create = ChannelViewSet.as_view({"get": "list", "post": "create"})
detail = ChannelViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

urlpatterns = [
    path("<uuid:server_id>/", list_create, name="channel-list"),
    path("<uuid:server_id>/<uuid:pk>/", detail, name="channel-detail"),
]
