"""Views exposing activity analytics endpoints."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .analytics import ActivityAnalytics, PresenceAnalytics
from apps.servers.models import Server


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_activity_analytics(request):
    days = int(request.query_params.get("days", 30))
    stats = ActivityAnalytics.get_user_activity_stats(request.user, days=days)
    stats["presence_timeline"] = ActivityAnalytics.get_presence_timeline(request.user, days=min(days, 14))
    stats["presence_summary"] = PresenceAnalytics.get_user_presence_summary(request.user, days=min(days, 14))
    return Response(stats)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def server_activity_analytics(request, server_id):
    server = get_object_or_404(Server, id=server_id)
    if not server.members.filter(user=request.user).exists():
        return Response({"detail": "Not a member of this server."}, status=status.HTTP_403_FORBIDDEN)

    days = int(request.query_params.get("days", 30))
    stats = ActivityAnalytics.get_server_activity_stats(server, days=days)
    stats["presence_heatmap"] = PresenceAnalytics.get_server_presence_heatmap(server, days=min(days, 14))
    return Response(stats)
