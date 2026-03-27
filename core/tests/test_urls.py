"""Tests for URL configuration."""

import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
class TestURLConfiguration:
    def test_admin_not_exposed_in_production(self, client):
        """Admin panel is only registered when DEBUG=True (test runs with DEBUG=False)."""
        response = client.get("/admin/")
        assert response.status_code == 404

    def test_api_docs_not_exposed_in_production(self, client):
        """API docs are disabled when DEBUG=False."""
        response = client.get("/api/v1/docs")
        assert response.status_code == 404

    def test_api_health_accessible(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
