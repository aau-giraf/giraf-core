"""Tests for URL configuration."""

import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
class TestURLConfiguration:
    def test_admin_not_accessible_when_debug_false(self, client, settings):
        """Admin panel should not be accessible in production (DEBUG=False)."""
        settings.DEBUG = False
        response = client.get("/admin/")
        assert response.status_code == 404

    def test_api_health_accessible(self, client):
        """Health check endpoint should always be accessible."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
