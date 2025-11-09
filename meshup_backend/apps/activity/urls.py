"""URL routing for activity APIs."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .analytics_views import server_activity_analytics, user_activity_analytics
from .views import (
    ActivityLogViewSet,
    ActivityStreakViewSet,
    OnlinePresenceViewSet,
    ShareableActivityViewSet,
    UserActivityViewSet,
)

router = DefaultRouter()
router.register(r"user-activity", UserActivityViewSet, basename="user-activity")
router.register(r"logs", ActivityLogViewSet, basename="activity-log")
router.register(r"streaks", ActivityStreakViewSet, basename="activity-streak")
router.register(r"shareable", ShareableActivityViewSet, basename="shareable-activity")
router.register(r"presence", OnlinePresenceViewSet, basename="online-presence")

urlpatterns = [
    path("", include(router.urls)),
    path("analytics/user/", user_activity_analytics, name="activity-user-analytics"),
    path("analytics/server/<uuid:server_id>/", server_activity_analytics, name="activity-server-analytics"),
]
