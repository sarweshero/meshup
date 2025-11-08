"""URL configuration for task endpoints."""
from django.urls import path

from .views import TaskViewSet

list_create = TaskViewSet.as_view({"get": "list", "post": "create"})
detail = TaskViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})
comments = TaskViewSet.as_view({"get": "comments", "post": "comments"})
attachments = TaskViewSet.as_view({"post": "attachments"})
assign = TaskViewSet.as_view({"post": "assign"})
complete = TaskViewSet.as_view({"post": "complete"})

urlpatterns = [
    path("<uuid:server_id>/", list_create, name="task-list"),
    path("<uuid:server_id>/<uuid:pk>/", detail, name="task-detail"),
    path("<uuid:server_id>/<uuid:pk>/comments/", comments, name="task-comments"),
    path("<uuid:server_id>/<uuid:pk>/attachments/", attachments, name="task-attachments"),
    path("<uuid:server_id>/<uuid:pk>/assign/", assign, name="task-assign"),
    path("<uuid:server_id>/<uuid:pk>/complete/", complete, name="task-complete"),
]
