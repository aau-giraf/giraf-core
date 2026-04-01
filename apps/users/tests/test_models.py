"""Tests for the custom User model.

These tests define the expected behavior of the GIRAF User model.
Written BEFORE implementation — tests should FAIL initially, then pass
after the model is properly implemented.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
class TestUserCreation:
    """Test creating users via the model manager."""

    def test_create_user_with_required_fields(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        assert user.pk is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.check_password("testpass123")
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_without_username_raises(self):
        with pytest.raises(ValueError):
            User.objects.create_user(
                username="",
                email="test@example.com",
                password="testpass123",
            )

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_email_is_optional(self):
        """Email should not be required — some caretakers may not have one."""
        user = User.objects.create_user(
            username="noemail",
            password="testpass123",
        )
        assert user.pk is not None

    def test_display_name(self):
        """User should have a display_name property returning full name or username."""
        user = User.objects.create_user(
            username="jdoe",
            password="pass123",
            first_name="Jane",
            last_name="Doe",
        )
        assert user.display_name == "Jane Doe"

    def test_display_name_falls_back_to_username(self):
        user = User.objects.create_user(
            username="jdoe",
            password="pass123",
        )
        assert user.display_name == "jdoe"


@pytest.mark.django_db
class TestUserUniqueness:
    """Test uniqueness constraints."""

    def test_duplicate_username_raises(self):
        User.objects.create_user(username="unique", password="pass123")
        with pytest.raises(IntegrityError):
            User.objects.create_user(username="unique", password="pass456")

    def test_duplicate_email_allowed(self):
        """Multiple users can share an email (or have blank email).
        This matches the current weekplanner behavior."""
        User.objects.create_user(username="user1", email="shared@example.com", password="pass123")
        user2 = User.objects.create_user(username="user2", email="shared@example.com", password="pass456")
        assert user2.pk is not None


@pytest.mark.django_db
class TestUserStringRepresentation:
    def test_str_returns_username(self):
        user = User.objects.create_user(username="testuser", password="pass123")
        assert str(user) == "testuser"
