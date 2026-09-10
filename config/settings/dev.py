"""Development settings."""

import os

from config.settings.base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True
REGISTRATION_OPEN = True

SECRET_KEY = "django-insecure-dev-only-DO-NOT-USE-IN-PRODUCTION"  # noqa: S105

# Re-evaluate SIGNING_KEY now that SECRET_KEY is set. JWT_SECRET has to win
# over SECRET_KEY here: giraf-ai and weekplanner validate core-issued tokens
# locally with that shared key, so signing with the dev SECRET_KEY instead
# makes every cross-service call fail with an invalid signature.
NINJA_JWT["SIGNING_KEY"] = os.environ.get("JWT_SECRET", SECRET_KEY)  # noqa: F405
