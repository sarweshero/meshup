"""Custom REST framework throttles for authentication and messaging flows."""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginThrottle(AnonRateThrottle):
    """Tight rate limit for login attempts keyed by email."""

    scope = "auth_login"
    rate = "5/min"

    def get_cache_key(self, request, view):
        if request.method == "POST":
            email = (request.data or {}).get("email")
            if email:
                return f"login_attempt:{email.lower()}"
        return super().get_cache_key(request, view)


class RegistrationThrottle(AnonRateThrottle):
    """Limit registration attempts per client."""

    scope = "auth_register"
    rate = "3/hour"


class MessageThrottle(UserRateThrottle):
    """Throttle bursty message creation."""

    scope = "message_create"
    rate = "30/min"


class TaskThrottle(UserRateThrottle):
    """Throttle task operations per user."""

    scope = "task_operations"
    rate = "100/hour"


class BurstRateThrottle(UserRateThrottle):
    """Burst throttle applied globally for authenticated users."""

    scope = "burst"
    rate = "100/min"


class SustainedRateThrottle(UserRateThrottle):
    """Sustained throttle to keep long-term traffic in check."""

    scope = "sustained"
    rate = "10000/day"
