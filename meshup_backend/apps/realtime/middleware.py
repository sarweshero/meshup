"""Custom authentication middleware for websocket connections using JWT tokens."""
from __future__ import annotations

from typing import Optional
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils.functional import LazyObject
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@database_sync_to_async
def _get_user(user_id: str):
    return User.objects.get(id=user_id)


def _extract_token(scope) -> Optional[str]:
    query_string = scope.get("query_string", b"").decode()
    params = parse_qs(query_string)
    token = params.get("token", [None])[0]
    if token:
        return token

    for header_name, header_value in scope.get("headers", []):
        if header_name.decode().lower() == "authorization":
            value = header_value.decode()
            if value.lower().startswith("bearer "):
                return value.split(" ", 1)[1]
    return None


class JWTAuthMiddleware(BaseMiddleware):
    """Attach authenticated user to websocket scope using JWT access token."""

    async def __call__(self, scope, receive, send):
        scope_user = scope.get("user")
        if not isinstance(scope_user, LazyObject):
            scope["user"] = AnonymousUser()

        token = _extract_token(scope)
        if token:
            try:
                access_token = AccessToken(token)
                user = await _get_user(access_token["user_id"])
                scope["user"] = user
            except (TokenError, InvalidToken, KeyError, User.DoesNotExist):
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Convenience helper replicating AuthMiddlewareStack with JWT support."""

    return JWTAuthMiddleware(AuthMiddlewareStack(inner))
