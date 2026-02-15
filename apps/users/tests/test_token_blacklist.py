"""Tests for token blacklist (logout) functionality."""

import pytest
from django.test import Client

from apps.users.tests.factories import UserFactory


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
class TestTokenBlacklist:
    def _login(self, client):
        UserFactory(username="bluser", password="testpass123")
        resp = client.post(
            "/api/v1/token/pair",
            data={"username": "bluser", "password": "testpass123"},
            content_type="application/json",
        )
        data = resp.json()
        return data["access"], data["refresh"]

    def test_blacklist_endpoint_returns_200(self, client):
        _, refresh = self._login(client)
        resp = client.post(
            "/api/v1/token/blacklist",
            data={"refresh": refresh},
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_blacklisted_refresh_token_cannot_be_reused(self, client):
        _, refresh = self._login(client)

        # Blacklist the refresh token
        resp = client.post(
            "/api/v1/token/blacklist",
            data={"refresh": refresh},
            content_type="application/json",
        )
        assert resp.status_code == 200

        # Try to use the blacklisted refresh token
        resp = client.post(
            "/api/v1/token/refresh",
            data={"refresh": refresh},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_invalid_token_returns_error(self, client):
        resp = client.post(
            "/api/v1/token/blacklist",
            data={"refresh": "invalid-token"},
            content_type="application/json",
        )
        assert resp.status_code in (401, 422)
