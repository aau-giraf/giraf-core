"""Tests for URL configuration."""

from unittest.mock import patch

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
        data = response.json()
        assert data["status"] == "ok"
        assert data["db"] == "ok"

    def test_health_returns_503_when_db_unavailable(self, client):
        with patch("config.api.connection") as mock_conn:
            mock_conn.ensure_connection.side_effect = Exception("DB down")
            response = client.get("/api/v1/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["db"] == "unavailable"
