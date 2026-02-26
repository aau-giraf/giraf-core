"""Production settings."""

import os

from config.settings.base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# Enforce real secret key in production
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

# ---------------------------------------------------------------------------
# Security hardening (Django's built-in SecurityMiddleware handles these)
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "true").lower() != "false"
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# JWT — re-evaluate SIGNING_KEY now that SECRET_KEY has been overridden
# ---------------------------------------------------------------------------
NINJA_JWT["SIGNING_KEY"] = os.environ.get("JWT_SECRET", SECRET_KEY)  # noqa: F405

# ---------------------------------------------------------------------------
# Cache — Redis required in production for multi-process rate limiting
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    }
}
