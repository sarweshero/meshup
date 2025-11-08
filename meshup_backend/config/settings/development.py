"""Development settings for Meshup backend."""
from .base import *  # noqa: F401,F403

DEBUG = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK.update({  # type: ignore[attr-defined]
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    )
})
