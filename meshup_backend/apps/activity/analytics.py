"""Analytics helpers for user activity and presence."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from .models import ActivityLog, ActivityStreak, OnlinePresence, ShareableActivity, UserActivity


class ActivityAnalytics:
    """Compute aggregate statistics about user and server activity."""

    @staticmethod
    def get_user_activity_stats(user, days: int = 30) -> dict[str, object]:
        cutoff = timezone.now() - timedelta(days=days)
        logs = ActivityLog.objects.filter(user=user, created_at__gte=cutoff)
        streak = ActivityStreak.objects.filter(user=user).first()
        presence_sessions = OnlinePresence.objects.filter(user=user, came_online_at__gte=cutoff)
        user_activity = UserActivity.objects.filter(user=user).first()
        shareable = ShareableActivity.objects.filter(user=user).first()

        total_presence_seconds = 0.0
        servers_active: set[str] = set()
        for session in presence_sessions:
            end = session.went_offline_at or timezone.now()
            total_presence_seconds += (end - session.came_online_at).total_seconds()
            if session.server_id:
                servers_active.add(str(session.server_id))

        logs_by_type = {item["activity_type"]: item["count"] for item in logs.values("activity_type").annotate(count=Count("id"))}
        logs_by_day = ActivityAnalytics._group_logs_by_day(logs)

        stats: dict[str, object] = {
            "total_logs": logs.count(),
            "logs_by_type": logs_by_type,
            "logs_by_day": logs_by_day,
            "active_servers": list(servers_active),
            "total_presence_hours": round(total_presence_seconds / 3600, 2),
            "average_daily_presence_minutes": ActivityAnalytics._average_daily_minutes(total_presence_seconds, days),
            "current_status": user_activity.status if user_activity else "offline",
            "current_activity": user_activity.current_activity if user_activity else "idle",
            "current_shareable_activity": ActivityAnalytics._format_shareable(shareable),
            "streak": ActivityAnalytics._format_streak(streak),
        }
        return stats

    @staticmethod
    def get_server_activity_stats(server, days: int = 30) -> dict[str, object]:
        cutoff = timezone.now() - timedelta(days=days)
        logs = ActivityLog.objects.filter(server=server, created_at__gte=cutoff)
        presence_sessions = OnlinePresence.objects.filter(server=server, came_online_at__gte=cutoff)

        users_active = logs.values("user").distinct().count()
        active_channels = logs.values("channel").exclude(channel=None).annotate(count=Count("id")).order_by("-count")[:5]
        active_channels_formatted = []
        if active_channels:
            from apps.channels.models import Channel

            channel_map = {
                str(channel.id): channel
                for channel in Channel.objects.filter(id__in=[item["channel"] for item in active_channels if item["channel"]])
            }
            for item in active_channels:
                channel_id = item["channel"]
                if channel_id and str(channel_id) in channel_map:
                    channel = channel_map[str(channel_id)]
                    active_channels_formatted.append(
                        {
                            "id": str(channel.id),
                            "name": channel.name,
                            "activity_count": item["count"],
                        }
                    )

        total_presence_seconds = ActivityAnalytics._sum_presence_seconds(presence_sessions)

        stats: dict[str, object] = {
            "total_logs": logs.count(),
            "logs_by_type": {item["activity_type"]: item["count"] for item in logs.values("activity_type").annotate(count=Count("id"))},
            "unique_users": users_active,
            "active_channels": active_channels_formatted,
            "total_presence_hours": round(total_presence_seconds / 3600, 2),
            "average_session_minutes": ActivityAnalytics._average_session_minutes(presence_sessions),
        }
        return stats

    @staticmethod
    def get_presence_timeline(user, days: int = 7) -> list[dict[str, object]]:
        cutoff = timezone.now() - timedelta(days=days)
        sessions = OnlinePresence.objects.filter(user=user, came_online_at__gte=cutoff).order_by("-came_online_at")
        timeline = []
        for session in sessions:
            end = session.went_offline_at or timezone.now()
            timeline.append(
                {
                    "server_id": str(session.server_id),
                    "started_at": session.came_online_at,
                    "ended_at": session.went_offline_at,
                    "duration_minutes": round((end - session.came_online_at).total_seconds() / 60, 2),
                    "is_online": session.is_online,
                }
            )
        return timeline

    @staticmethod
    def _group_logs_by_day(logs_queryset) -> dict[str, int]:
        bucket = defaultdict(int)
        for log in logs_queryset.values("created_at"):
            day = log["created_at"].date().isoformat()
            bucket[day] += 1
        return dict(bucket)

    @staticmethod
    def _average_daily_minutes(total_seconds: float, days: int) -> float:
        if days <= 0:
            return 0.0
        return round((total_seconds / 60) / days, 2)

    @staticmethod
    def _sum_presence_seconds(sessions) -> float:
        total = 0.0
        now = timezone.now()
        for session in sessions:
            end = session.went_offline_at or now
            total += (end - session.came_online_at).total_seconds()
        return total

    @staticmethod
    def _average_session_minutes(sessions) -> float:
        durations = []
        now = timezone.now()
        for session in sessions:
            end = session.went_offline_at or now
            durations.append((end - session.came_online_at).total_seconds() / 60)
        if not durations:
            return 0.0
        return round(sum(durations) / len(durations), 2)

    @staticmethod
    def _format_streak(streak: ActivityStreak | None) -> dict[str, object] | None:
        if not streak:
            return None
        return {
            "current_streak": streak.current_streak,
            "best_streak": streak.best_streak,
            "last_active_date": streak.last_active_date,
            "streak_started_at": streak.streak_started_at,
        }

    @staticmethod
    def _format_shareable(shareable: ShareableActivity | None) -> dict[str, object] | None:
        if not shareable:
            return None
        progress_percent = 0.0
        if shareable.duration_seconds and shareable.duration_seconds > 0:
            progress_percent = round((shareable.progress_seconds / shareable.duration_seconds) * 100, 2)
        return {
            "activity_type": shareable.activity_type,
            "title": shareable.title,
            "service_name": shareable.service_name,
            "progress_percent": progress_percent,
            "is_public": shareable.is_public,
        }


class PresenceAnalytics:
    """Helper routines for presence heatmaps and occupancy stats."""

    @staticmethod
    def get_server_presence_heatmap(server, days: int = 7) -> dict[str, dict[str, int]]:
        cutoff = timezone.now() - timedelta(days=days)
        sessions = OnlinePresence.objects.filter(server=server, came_online_at__gte=cutoff)
        heatmap: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for session in sessions:
            start = session.came_online_at
            end = session.went_offline_at or timezone.now()
            current = start
            while current <= end:
                day = current.date().isoformat()
                hour = f"{current.hour:02d}:00"
                heatmap[day][hour] += 1
                current += timedelta(hours=1)
        # Convert nested defaultdicts to regular dicts
        return {day: dict(hours) for day, hours in heatmap.items()}

    @staticmethod
    def get_user_presence_summary(user, days: int = 7) -> dict[str, object]:
        cutoff = timezone.now() - timedelta(days=days)
        sessions = OnlinePresence.objects.filter(user=user, came_online_at__gte=cutoff)
        total_seconds = ActivityAnalytics._sum_presence_seconds(sessions)
        return {
            "total_hours": round(total_seconds / 3600, 2),
            "average_session_minutes": ActivityAnalytics._average_session_minutes(sessions),
            "session_count": sessions.count(),
        }
