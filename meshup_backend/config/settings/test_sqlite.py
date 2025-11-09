"""Test settings using in-memory SQLite for local pytest runs."""
from __future__ import annotations

from .development import *  # noqa: F401,F403


DATABASES["default"] = {
	"ENGINE": "django.db.backends.sqlite3",
	"NAME": str(BASE_DIR / "test_db.sqlite3"),
}

CHANNEL_LAYERS = {
	"default": {
		"BACKEND": "channels.layers.InMemoryChannelLayer",
	}
}

SWAGGER_USE_COMPAT_RENDERERS = False