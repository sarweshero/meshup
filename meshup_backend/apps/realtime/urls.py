"""URL routes for realtime auxiliary APIs."""
from django.urls import path

from .views import RealtimeMetadataView

app_name = "realtime"

urlpatterns = [
    path("meta/", RealtimeMetadataView.as_view(), name="metadata"),
]
