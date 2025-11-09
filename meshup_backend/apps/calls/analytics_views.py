"""Views for call analytics and reporting."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .analytics import CallAnalytics, CallQualityAnalyzer
from .models import CallParticipant, CallSession
from apps.servers.models import Server


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_call_analytics(request):
    days = int(request.query_params.get("days", 30))
    stats = CallAnalytics.get_user_call_stats(request.user, days=days)
    return Response(stats)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def server_call_analytics(request, server_id):
    server = get_object_or_404(Server, id=server_id)
    if not server.members.filter(user=request.user).exists():
        return Response({"error": "Not a member of this server"}, status=status.HTTP_403_FORBIDDEN)
    days = int(request.query_params.get("days", 30))
    stats = CallAnalytics.get_server_call_stats(server, days=days)
    return Response(stats)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def call_quality_assessment(request, call_id, participant_id):
    call = get_object_or_404(CallSession, id=call_id)
    participant = get_object_or_404(CallParticipant, id=participant_id, call=call)
    metrics = list(participant.quality_metrics.all().order_by("-recorded_at")[:100])
    trend = CallQualityAnalyzer.get_quality_trend(participant)
    latest_metrics = metrics[0] if metrics else None
    return Response(
        {
            "participant": participant.user.username,
            "sample_count": len(metrics),
            "trend": trend,
            "latest_metrics": {
                "latency_ms": participant.latency_ms if latest_metrics else None,
                "packet_loss_percent": participant.packet_loss_rate if latest_metrics else None,
            },
        }
    )
