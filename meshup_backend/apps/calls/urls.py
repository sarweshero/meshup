"""URL routing for voice and video calls."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .analytics_views import call_quality_assessment, server_call_analytics, user_call_analytics
from .views import CallSessionViewSet

router = DefaultRouter()
router.register(r"", CallSessionViewSet, basename="call")

urlpatterns = [
    path("", include(router.urls)),
    path("analytics/user/", user_call_analytics, name="call-user-analytics"),
    path("analytics/server/<uuid:server_id>/", server_call_analytics, name="call-server-analytics"),
    path(
        "<uuid:call_id>/participants/<uuid:participant_id>/quality/",
        call_quality_assessment,
        name="call-quality-assessment",
    ),
]