"""URL configuration for poll endpoints."""
from django.urls import path

from .views import PollViewSet

list_create = PollViewSet.as_view({"get": "list", "post": "create"})
detail = PollViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})
vote = PollViewSet.as_view({"post": "vote"})
unvote = PollViewSet.as_view({"delete": "unvote"})
results = PollViewSet.as_view({"get": "results"})
close = PollViewSet.as_view({"post": "close"})
comments = PollViewSet.as_view({"get": "comments", "post": "comments"})

urlpatterns = [
    path("<uuid:server_id>/", list_create, name="poll-list"),
    path("<uuid:server_id>/<uuid:pk>/", detail, name="poll-detail"),
    path("<uuid:server_id>/<uuid:pk>/vote/", vote, name="poll-vote"),
    path("<uuid:server_id>/<uuid:pk>/unvote/", unvote, name="poll-unvote"),
    path("<uuid:server_id>/<uuid:pk>/results/", results, name="poll-results"),
    path("<uuid:server_id>/<uuid:pk>/close/", close, name="poll-close"),
    path("<uuid:server_id>/<uuid:pk>/comments/", comments, name="poll-comments"),
]
