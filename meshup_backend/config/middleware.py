"""Custom middleware for audit logging sensitive requests."""
import logging
import uuid
from typing import Tuple

from django.utils.deprecation import MiddlewareMixin

from apps.auth.models import AuditLog

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(MiddlewareMixin):
    """Capture audit trail for sensitive or state-changing API requests."""

    SENSITIVE_PATHS = [
        "/api/v1/auth/",
        "/api/v1/servers/",
        "/api/v1/tasks/",
        "/api/v1/roles/",
    ]

    @staticmethod
    def _client_ip(request) -> str:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @staticmethod
    def _user_agent(request) -> str:
        return request.META.get("HTTP_USER_AGENT", "")[:500]

    def _should_audit(self, request) -> bool:
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            return True
        return any(request.path.startswith(path) for path in self.SENSITIVE_PATHS)

    def process_response(self, request, response):  # noqa: D401 - DRF signature
        if not self._should_audit(request):
            return response

        try:
            user = request.user if request.user.is_authenticated else None
            action = self.get_action_type(request.method, request.path)
            resource_type, resource_id = self.extract_resource_info(request.path)

            AuditLog.objects.create(
                user=user,
                action=action,
                severity=self._severity(response.status_code),
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name="",
                ip_address=self._client_ip(request) or "0.0.0.0",
                user_agent=self._user_agent(request),
                method=request.method,
                endpoint=request.path,
                status_code=response.status_code,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to record audit log: %s", exc)

        return response

    @staticmethod
    def get_action_type(method: str, path: str) -> str:
        lowered_path = path.lower()
        if "auth/login" in lowered_path:
            return "login"
        if "auth/logout" in lowered_path:
            return "logout"
        if "auth/password" in lowered_path:
            return "password_change"
        if method == "POST":
            return "resource_create"
        if method in {"PUT", "PATCH"}:
            return "resource_update"
        if method == "DELETE":
            return "resource_delete"
        return "unknown"

    @staticmethod
    def extract_resource_info(path: str) -> Tuple[str, uuid.UUID | None]:
        parts = [segment for segment in path.strip("/").split("/") if segment]
        resource_type = "unknown"
        resource_id: uuid.UUID | None = None

        if len(parts) >= 3:
            resource_type = parts[2]
        elif parts:
            resource_type = parts[0]

        if len(parts) >= 4:
            try:
                resource_id = uuid.UUID(parts[3])
            except (ValueError, AttributeError):
                resource_id = None

        return resource_type, resource_id

    @staticmethod
    def _severity(status_code: int) -> str:
        if status_code >= 500:
            return "critical"
        if status_code >= 400:
            return "warning"
        return "info"
