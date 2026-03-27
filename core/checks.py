"""Django system checks for security configuration."""

from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.security, deploy=True)
def check_cors_not_open(app_configs, **kwargs):
    """Warn if CORS allows all origins outside of DEBUG mode."""
    errors = []
    if getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False) and not settings.DEBUG:
        errors.append(
            Warning(
                "CORS_ALLOW_ALL_ORIGINS is True while DEBUG is False.",
                hint="Set CORS_ALLOW_ALL_ORIGINS = False and configure "
                "CORS_ALLOWED_ORIGINS with explicit origins.",
                id="giraf.W001",
            )
        )
    return errors
