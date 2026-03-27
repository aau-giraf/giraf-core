"""Tests for authentication endpoints.

Written BEFORE implementation — tests define the expected auth behavior.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.users.tests.factories import UserFactory
from conftest import auth_header_for_user

User = get_user_model()


@pytest.fixture
def existing_user(db):
    return UserFactory(username="existing", password="testpass123")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRegistration:
    @pytest.fixture(autouse=True)
    def _open_registration(self, settings):
        settings.REGISTRATION_OPEN = True

    def test_register_closed_returns_403(self, client, settings):
        settings.REGISTRATION_OPEN = False
        response = client.post(
            "/api/v1/auth/register",
            data={"username": "newuser", "password": "Str0ngPass!"},
            content_type="application/json",
        )
        assert response.status_code == 403
        assert User.objects.filter(username="newuser").exists() is False

    def test_register_creates_user(self, client):
        response = client.post(
            "/api/v1/auth/register",
            data={
                "username": "newuser",
                "password": "Str0ngPass!",
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "User",
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert "password" not in data  # Never expose password
        assert User.objects.filter(username="newuser").exists()

    def test_register_duplicate_username_fails(self, client, existing_user):
        response = client.post(
            "/api/v1/auth/register",
            data={
                "username": "existing",
                "password": "Str0ngPass!",
            },
            content_type="application/json",
        )
        assert response.status_code == 409

    def test_register_weak_password_fails(self, client):
        response = client.post(
            "/api/v1/auth/register",
            data={
                "username": "weakuser",
                "password": "123",
            },
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_register_missing_username_fails(self, client):
        response = client.post(
            "/api/v1/auth/register",
            data={
                "password": "Str0ngPass!",
            },
            content_type="application/json",
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login (token obtain pair)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLogin:
    def test_login_returns_token_pair(self, client, existing_user):
        response = client.post(
            "/api/v1/token/pair",
            data={
                "username": "existing",
                "password": "testpass123",
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access" in data
        assert "refresh" in data

    def test_login_wrong_password_fails(self, client, existing_user):
        response = client.post(
            "/api/v1/token/pair",
            data={
                "username": "existing",
                "password": "wrongpassword",
            },
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_login_nonexistent_user_fails(self, client):
        response = client.post(
            "/api/v1/token/pair",
            data={
                "username": "nonexistent",
                "password": "testpass123",
            },
            content_type="application/json",
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTokenRefresh:
    def test_refresh_returns_new_access_token(self, client, existing_user):
        # First, login to get tokens
        login_resp = client.post(
            "/api/v1/token/pair",
            data={"username": "existing", "password": "testpass123"},
            content_type="application/json",
        )
        refresh_token = login_resp.json()["refresh"]

        # Now refresh
        response = client.post(
            "/api/v1/token/refresh",
            data={"refresh": refresh_token},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access" in data

    def test_refresh_with_invalid_token_fails(self, client):
        response = client.post(
            "/api/v1/token/refresh",
            data={"refresh": "invalid-token"},
            content_type="application/json",
        )
        assert response.status_code in (401, 422)


# ---------------------------------------------------------------------------
# GET /users/me — authenticated user profile
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUsersMe:
    def test_me_returns_current_user(self, client, existing_user):
        headers = auth_header_for_user(existing_user)
        response = client.get("/api/v1/users/me", **headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "existing"
        assert data["id"] == existing_user.id
        assert "password" not in data

    def test_me_unauthenticated_returns_401(self, client):
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    def test_me_invalid_token_returns_401(self, client):
        response = client.get(
            "/api/v1/users/me",
            HTTP_AUTHORIZATION="Bearer invalid-token",
        )
        assert response.status_code == 401
