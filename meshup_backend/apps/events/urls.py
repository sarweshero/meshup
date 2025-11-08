"""URL configuration for event endpoints."""
from django.urls import path

from .views import EventViewSet

list_create = EventViewSet.as_view({"get": "list", "post": "create"})
detail = EventViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})
rsvp = EventViewSet.as_view({"post": "rsvp"})
calendar = EventViewSet.as_view({"get": "calendar"})
upcoming = EventViewSet.as_view({"get": "upcoming"})

urlpatterns = [
    path("<uuid:server_id>/", list_create, name="event-list"),
    path("<uuid:server_id>/<uuid:pk>/", detail, name="event-detail"),
    path("<uuid:server_id>/<uuid:pk>/rsvp/", rsvp, name="event-rsvp"),
    path("<uuid:server_id>/calendar/", calendar, name="event-calendar"),
    path("<uuid:server_id>/upcoming/", upcoming, name="event-upcoming"),
]
