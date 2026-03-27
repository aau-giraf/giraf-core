"""Tests for security system checks."""

import pytest

from core.checks import check_cors_not_open


class TestCorsCheck:
    def test_warns_when_cors_open_without_debug(self, settings):
        settings.CORS_ALLOW_ALL_ORIGINS = True
        settings.DEBUG = False

        warnings = check_cors_not_open(app_configs=None)

        assert len(warnings) == 1
        assert warnings[0].id == "giraf.W001"

    def test_no_warning_when_cors_open_with_debug(self, settings):
        settings.CORS_ALLOW_ALL_ORIGINS = True
        settings.DEBUG = True

        warnings = check_cors_not_open(app_configs=None)

        assert len(warnings) == 0

    def test_no_warning_when_cors_restricted(self, settings):
        settings.CORS_ALLOW_ALL_ORIGINS = False
        settings.DEBUG = False

        warnings = check_cors_not_open(app_configs=None)

        assert len(warnings) == 0
