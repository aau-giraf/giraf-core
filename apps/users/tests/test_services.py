import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.users.models import User
from apps.users.services import UserService
from core.exceptions import BusinessValidationError, ConflictError


@pytest.fixture
def registered_user(db):
    return UserService.register(
        username="testuser",
        password="StrongPassword123!",
        email="test@example.com",
        first_name="Test",
        last_name="User",
    )


@pytest.mark.django_db
class TestUserService:
    def test_register_duplicate_username(self, registered_user):
        """Test that registering a duplicate username raises ConflictError."""
        with pytest.raises(ConflictError):
            UserService.register(username="testuser", password="AnotherStrongPassword123!")

    def test_change_password_incorrect_old_password(self, registered_user):
        """Test that changing password with wrong old password raises BusinessValidationError."""
        with pytest.raises(BusinessValidationError):
            UserService.change_password(
                user_id=registered_user.id, old_password="wrongpassword", new_password="NewStrongPassword123!"
            )

    def test_change_password_weak_new_password(self, registered_user):
        """Test that changing password to weak password raises BusinessValidationError."""
        with pytest.raises(BusinessValidationError):
            UserService.change_password(
                user_id=registered_user.id, old_password="StrongPassword123!", new_password="weak"
            )

    def test_delete_user(self, registered_user):
        """Test deactivating a user (soft delete)."""
        UserService.delete_user(user_id=registered_user.id)
        user = User.objects.get(id=registered_user.id)
        assert not user.is_active

    def test_upload_profile_picture_oversized(self, registered_user):
        """Test that uploading an oversized image raises BusinessValidationError."""
        buf = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buf, format="PNG")
        buf.seek(0)
        file = SimpleUploadedFile("big.png", buf.read() + b"\x00" * (21 * 1024 * 1024), content_type="image/png")
        with pytest.raises(BusinessValidationError):
            UserService.upload_profile_picture(user_id=registered_user.id, file=file)

    def test_upload_profile_picture_corrupted(self, registered_user):
        """Test that uploading a corrupted image raises BusinessValidationError."""
        file = SimpleUploadedFile("fake.png", b"not an image at all", content_type="image/png")
        with pytest.raises(BusinessValidationError):
            UserService.upload_profile_picture(user_id=registered_user.id, file=file)
