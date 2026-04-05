"""Development settings."""

from config.settings.base import *  # noqa: F403

DEBUG = True
SECRET_KEY = "django-insecure-dev-only-DO-NOT-USE-IN-PRODUCTION"  # noqa: S105
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True
REGISTRATION_OPEN = True

# Re-evaluate SIGNING_KEY now that SECRET_KEY is set
NINJA_JWT["SIGNING_KEY"] = SECRET_KEY  # type: ignore[name-defined]  # noqa: F405
