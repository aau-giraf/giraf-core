"""Test settings — SQLite, fast, no external dependencies."""

from datetime import timedelta

from config.settings.base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "django-insecure-test-only"  # noqa: S105

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Shorter token lifetimes for testing edge cases
NINJA_JWT = {
    **NINJA_JWT,  # type: ignore[name-defined]  # noqa: F405
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(minutes=30),
    "SIGNING_KEY": SECRET_KEY,
}
