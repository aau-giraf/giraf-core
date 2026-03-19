"""Tests for URL configuration."""

import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
class TestURLConfiguration:
    def test_admin_accessible_in_all_environments(self, client, settings):
        """Admin panel should be accessible regardless of DEBUG setting."""
        settings.DEBUG = False
        response = client.get("/admin/")
        # Redirects to login page (302), not 404
        assert response.status_code == 302

    def test_api_health_accessible(self, client):
        """Health check endpoint should always be accessible."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
