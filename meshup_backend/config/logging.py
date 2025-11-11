"""Custom logging filters and helpers for the Meshup project."""
from __future__ import annotations

import logging
from typing import Any


class RequestLogFilter(logging.Filter):
    """Attach request-specific context (IP, user agent, etc.) to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        request = getattr(record, "request", None)

        client_ip = "-"
        http_method = "-"
        full_path = getattr(record, "path", getattr(record, "pathname", "-"))
        user_agent = "-"
        referer = "-"
        username = "anonymous"
        user_id: Any = "-"

        if request is not None:
            client_ip = self._get_client_ip(request)
            http_method = getattr(request, "method", "-")
            try:  # Guard against non-HTTP requests that still attach a path attribute
                full_path = request.get_full_path()
            except Exception:  # pragma: no cover - defensive fallback
                full_path = getattr(request, "path", "-")
            user_agent = request.META.get("HTTP_USER_AGENT", "-")
            referer = request.META.get("HTTP_REFERER", "-")
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                username = getattr(user, "username", "authenticated")
                user_id = getattr(user, "id", "-")
            elif user is not None:
                username = "anonymous"
                user_id = "-"

        record.client_ip = client_ip
        record.http_method = http_method
        record.full_path = full_path
        record.user_agent = user_agent
        record.referer = referer
        record.username = username
        record.user_id = user_id

        return True

    @staticmethod
    def _get_client_ip(request) -> str:
        header = request.META.get("HTTP_X_FORWARDED_FOR")
        if header:
            # RFC 7239: first entry is the original client
            client_ip = header.split(",")[0].strip()
            if client_ip:
                return client_ip
        remote_addr = request.META.get("REMOTE_ADDR")
        return remote_addr or "-"
