"""Testing settings for Meshup backend."""
from .base import *  # noqa: F401,F403

DEBUG = False

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

DATABASES["default"].update({  # type: ignore[index]
    "NAME": "test_meshup_db",
})
