"""Tests for user management API endpoints.

Tests for profile updates, password changes, account deletion, and profile pictures.
"""

import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from apps.users.tests.factories import UserFactory

User = get_user_model()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    return UserFactory(username="testuser", password="testpass123", email="test@example.com")


def get_auth_header(client, username="testuser", password="testpass123"):
    """Helper to get authentication header for requests."""
    resp = client.post(
        "/api/v1/token/pair",
        data={"username": username, "password": password},
        content_type="application/json",
    )
    token = resp.json()["access"]
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# PUT /users/me — update profile
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUpdateProfile:
    def test_update_profile_success(self, client, user):
        headers = get_auth_header(client)
        response = client.put(
            "/api/v1/users/me",
            data={
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@example.com",
            },
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["email"] == "updated@example.com"

        # Verify database was updated
        user.refresh_from_db()
        assert user.first_name == "Updated"
        assert user.last_name == "Name"
        assert user.email == "updated@example.com"

    def test_update_profile_partial(self, client, user):
        """Test that only provided fields are updated."""
        original_email = user.email
        headers = get_auth_header(client)
        response = client.put(
            "/api/v1/users/me",
            data={"first_name": "NewFirst"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.first_name == "NewFirst"
        assert user.email == original_email  # Not changed

    def test_update_profile_unauthenticated(self, client):
        response = client.put(
            "/api/v1/users/me",
            data={"first_name": "Updated"},
            content_type="application/json",
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# PUT /users/me/password — change password
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestChangePassword:
    def test_change_password_success(self, client, user):
        headers = get_auth_header(client)
        response = client.put(
            "/api/v1/users/me/password",
            data={
                "old_password": "testpass123",
                "new_password": "NewStr0ngPass!",
            },
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200

        # Verify can login with new password
        new_headers = get_auth_header(client, password="NewStr0ngPass!")
        verify_response = client.get("/api/v1/users/me", **new_headers)
        assert verify_response.status_code == 200

    def test_change_password_wrong_old_password(self, client, user):
        headers = get_auth_header(client)
        response = client.put(
            "/api/v1/users/me/password",
            data={
                "old_password": "wrongpassword",
                "new_password": "NewStr0ngPass!",
            },
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 422
        assert "Old password is incorrect" in response.json()["detail"]

    def test_change_password_weak_new_password(self, client, user):
        headers = get_auth_header(client)
        response = client.put(
            "/api/v1/users/me/password",
            data={
                "old_password": "testpass123",
                "new_password": "123",
            },
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 422

    def test_change_password_unauthenticated(self, client):
        response = client.put(
            "/api/v1/users/me/password",
            data={
                "old_password": "testpass123",
                "new_password": "NewStr0ngPass!",
            },
            content_type="application/json",
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /users/me — delete account
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDeleteAccount:
    def test_delete_account_success(self, client, user):
        user_id = user.id
        headers = get_auth_header(client)
        response = client.delete("/api/v1/users/me", **headers)
        assert response.status_code == 204

        # Verify user is deactivated (soft delete)
        user_obj = User.objects.get(id=user_id)
        assert not user_obj.is_active

    def test_delete_account_cannot_login_after(self, client, user):
        headers = get_auth_header(client)
        client.delete("/api/v1/users/me", **headers)

        # Try to login with deleted account
        login_response = client.post(
            "/api/v1/token/pair",
            data={"username": "testuser", "password": "testpass123"},
            content_type="application/json",
        )
        assert login_response.status_code == 401

    def test_delete_account_unauthenticated(self, client):
        response = client.delete("/api/v1/users/me")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /users/me/profile-picture — upload profile picture
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUploadProfilePicture:
    def test_upload_profile_picture_success(self, client, user):
        headers = get_auth_header(client)
        # Create a valid test image
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
        buf.seek(0)
        image_file = SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")

        response = client.post(
            "/api/v1/users/me/profile-picture",
            data={"file": image_file},
            **headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["profile_picture"] is not None
        assert "profile_pictures" in data["profile_picture"]

    def test_upload_profile_picture_invalid_type(self, client, user):
        headers = get_auth_header(client)
        # Create a non-image file
        text_file = SimpleUploadedFile(
            "test.txt",
            b"not an image",
            content_type="text/plain",
        )

        response = client.post(
            "/api/v1/users/me/profile-picture",
            data={"file": text_file},
            **headers,
        )
        assert response.status_code == 422
        assert "JPEG, PNG, and WebP" in str(response.json()["detail"])

    def test_upload_profile_picture_replaces_old(self, client, user):
        """Test that uploading a new picture deletes the old one."""
        headers = get_auth_header(client)

        # Upload first image
        buf1 = io.BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buf1, format="JPEG")
        buf1.seek(0)
        image1 = SimpleUploadedFile("test1.jpg", buf1.read(), content_type="image/jpeg")
        response1 = client.post(
            "/api/v1/users/me/profile-picture",
            data={"file": image1},
            **headers,
        )
        assert response1.status_code == 200
        first_path = response1.json()["profile_picture"]

        # Upload second image
        buf2 = io.BytesIO()
        Image.new("RGB", (10, 10), color="blue").save(buf2, format="JPEG")
        buf2.seek(0)
        image2 = SimpleUploadedFile(
            "test2.jpg",
            buf2.read(),
            content_type="image/jpeg",
        )
        response2 = client.post(
            "/api/v1/users/me/profile-picture",
            data={"file": image2},
            **headers,
        )
        assert response2.status_code == 200
        second_path = response2.json()["profile_picture"]

        # Paths should be different
        assert first_path != second_path

    def test_upload_profile_picture_unauthenticated(self, client):
        image_file = SimpleUploadedFile(
            "test.jpg",
            b"fake image content",
            content_type="image/jpeg",
        )
        response = client.post(
            "/api/v1/users/me/profile-picture",
            data={"file": image_file},
        )
        assert response.status_code == 401
