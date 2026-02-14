"""Test settings — SQLite, fast, no external dependencies."""
from datetime import timedelta

from config.settings.base import *  # noqa: F401, F403

DEBUG = False

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
}
