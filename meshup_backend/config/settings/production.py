"""Production settings for Meshup backend."""
from .base import *  # noqa: F401,F403

DEBUG = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

REST_FRAMEWORK.update({  # type: ignore[attr-defined]
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",)
})
