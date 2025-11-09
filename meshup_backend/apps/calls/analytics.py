"""Call analytics and reporting utilities."""

from __future__ import annotations

import statistics
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone

from .models import CallParticipant, CallQualityMetric, CallSession


class CallAnalytics:
    """Compute aggregate statistics for call usage."""

    @staticmethod
    def get_user_call_stats(user, days: int = 30) -> dict[str, object]:
        cutoff_date = timezone.now() - timedelta(days=days)
        calls = (
            CallSession.objects.filter(Q(initiator=user) | Q(participants__user=user), created_at__gte=cutoff_date)
            .distinct()
        )

        stats: dict[str, object] = {
            "total_calls": calls.count(),
            "total_duration_hours": 0,
            "average_duration_minutes": 0,
            "average_participants": 0,
            "calls_by_type": {},
            "calls_by_status": {},
            "call_quality_avg": {},
        }

        total_duration = sum(call.get_duration() for call in calls)
        stats["total_duration_hours"] = round(total_duration / 3600, 2)

        if calls.exists():
            stats["average_duration_minutes"] = round((total_duration / calls.count()) / 60, 2) if calls.count() else 0
            stats["average_participants"] = round(
                calls.aggregate(avg_participants=Avg("total_participants"))["avg_participants"] or 0, 1
            )

        stats["calls_by_type"] = dict(calls.values_list("call_type").annotate(count=Count("id")))
        stats["calls_by_status"] = dict(calls.values_list("status").annotate(count=Count("id")))

        quality_metrics = CallQualityMetric.objects.filter(participant__call__in=calls)
        if quality_metrics.exists():
            stats["call_quality_avg"] = {
                "avg_packet_loss_percent": round(
                    quality_metrics.aggregate(avg_loss=Avg("participant__packet_loss_rate"))["avg_loss"] or 0, 2
                ),
                "avg_latency_ms": round(
                    quality_metrics.aggregate(avg_latency=Avg("participant__latency_ms"))["avg_latency"] or 0, 1
                ),
                "avg_bandwidth_mbps": round(
                    quality_metrics.aggregate(avg_bw=Avg("participant__bandwidth_mbps"))["avg_bw"] or 0, 2
                ),
            }

        return stats

    @staticmethod
    def get_server_call_stats(server, days: int = 30) -> dict[str, object]:
        cutoff_date = timezone.now() - timedelta(days=days)
        calls = CallSession.objects.filter(server=server, created_at__gte=cutoff_date)

        stats: dict[str, object] = {
            "total_calls": calls.count(),
            "total_call_hours": 0,
            "unique_participants": 0,
            "peak_concurrent_calls": 0,
            "most_active_channel": None,
            "call_success_rate": 0,
        }

        total_duration = sum(call.get_duration() for call in calls)
        stats["total_call_hours"] = round(total_duration / 3600, 2)

        participants = CallParticipant.objects.filter(
            call__server=server,
            call__created_at__gte=cutoff_date,
        ).values("user").distinct()
        stats["unique_participants"] = participants.count()

        ended_calls = calls.filter(status="ended").count()
        stats["call_success_rate"] = round((ended_calls / calls.count()) * 100, 2) if calls.count() else 0

        channel_activity = calls.values("channel").annotate(count=Count("id")).order_by("-count").first()
        if channel_activity and channel_activity["channel"]:
            from apps.channels.models import Channel

            channel = Channel.objects.filter(id=channel_activity["channel"]).first()
            if channel:
                stats["most_active_channel"] = {
                    "id": str(channel.id),
                    "name": channel.name,
                    "call_count": channel_activity["count"],
                }

        return stats


class CallQualityAnalyzer:
    """Assess call quality trends."""

    @staticmethod
    def assess_connection_quality(metrics_list: list[CallQualityMetric]) -> str:
        if not metrics_list:
            return "unknown"
        packet_losses = [metric.participant.packet_loss_rate for metric in metrics_list]
        avg_packet_loss = statistics.mean(packet_losses)
        if avg_packet_loss < 0.5:
            return "excellent"
        if avg_packet_loss < 1.5:
            return "good"
        if avg_packet_loss < 3.0:
            return "fair"
        return "poor"

    @staticmethod
    def get_quality_trend(call_participant: CallParticipant, last_n_samples: int = 20) -> dict[str, object]:
        metrics = CallQualityMetric.objects.filter(participant=call_participant).order_by("-recorded_at")[:last_n_samples]
        if not metrics:
            return {"sample_count": 0, "quality_assessments": [], "avg_latency_ms": 0}

        quality_assessments = [CallQualityAnalyzer.assess_connection_quality([metric]) for metric in metrics]
        avg_latency = sum(metric.participant.latency_ms for metric in metrics) / len(metrics)

        return {
            "sample_count": len(metrics),
            "quality_assessments": quality_assessments,
            "avg_latency_ms": round(avg_latency, 1),
        }
