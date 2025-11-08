"""URL configuration for settings endpoints."""
from django.urls import path

from .views import NotificationPreferenceViewSet, ServerSettingsViewSet, UserSettingsViewSet

urlpatterns = [
    path(
        "user/",
        UserSettingsViewSet.as_view({"get": "list", "put": "update", "patch": "partial_update"}),
        name="user-settings",
    ),
    path(
        "servers/<uuid:server_id>/",
        ServerSettingsViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update"}),
        name="server-settings",
    ),
    path(
        "notifications/",
        NotificationPreferenceViewSet.as_view({"get": "list", "post": "create"}),
        name="notification-preferences",
    ),
    path(
        "notifications/<uuid:pk>/",
        NotificationPreferenceViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="notification-preference-detail",
    ),
]
