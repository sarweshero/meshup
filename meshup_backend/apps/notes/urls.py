"""URL configuration for note endpoints."""
from django.urls import path

from .views import NoteViewSet

list_create = NoteViewSet.as_view({"get": "list", "post": "create"})
detail = NoteViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})
versions = NoteViewSet.as_view({"get": "versions"})
restore = NoteViewSet.as_view({"post": "restore"})
pin = NoteViewSet.as_view({"post": "pin"})
lock = NoteViewSet.as_view({"post": "lock"})

urlpatterns = [
    path("<uuid:server_id>/", list_create, name="note-list"),
    path("<uuid:server_id>/<uuid:pk>/", detail, name="note-detail"),
    path("<uuid:server_id>/<uuid:pk>/versions/", versions, name="note-versions"),
    path("<uuid:server_id>/<uuid:pk>/restore/", restore, name="note-restore"),
    path("<uuid:server_id>/<uuid:pk>/pin/", pin, name="note-pin"),
    path("<uuid:server_id>/<uuid:pk>/lock/", lock, name="note-lock"),
]
