"""Business logic for user operations.

All business logic lives here — never in API endpoints.
"""

import mimetypes

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.users.models import User


class UserService:
    @staticmethod
    def register(
        *, username: str, password: str, email: str | None = None, first_name: str = "", last_name: str = ""
    ) -> User:
        """Create a new user with validated password.

        Raises:
            ValueError: If username already exists.
            ValidationError: If password doesn't meet strength requirements.
        """
        if User.objects.filter(username=username).exists():
            raise ValueError(f"Username '{username}' is already taken.")

        # Validate password strength using Django's validators
        try:
            validate_password(password)
        except ValidationError:
            raise

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email or "",
            first_name=first_name,
            last_name=last_name,
        )
        return user

    @staticmethod
    def update_user(user: User, **fields) -> User:
        """Update user profile fields. Only updates non-None values."""
        for key, value in fields.items():
            if value is not None:
                setattr(user, key, value)
        user.save()
        return user

    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> User:
        """Change user password with validation.

        Raises:
            ValueError: If old password is incorrect.
            ValidationError: If new password doesn't meet strength requirements.
        """
        if not user.check_password(old_password):
            raise ValueError("Old password is incorrect.")

        # Django's built-in password validators (min length 8, etc.)
        try:
            validate_password(new_password)
        except ValidationError:
            raise

        user.set_password(new_password)
        user.save()
        return user

    @staticmethod
    def delete_user(user: User) -> None:
        """Hard delete user account."""
        user.delete()

    @staticmethod
    def upload_profile_picture(user: User, file) -> User:
        """Upload and validate profile picture.

        Raises:
            ValidationError: If file type or size is invalid.
        """
        # Validate file type
        mime_type, _ = mimetypes.guess_type(file.name)
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if mime_type not in allowed_types:
            raise ValidationError("Only JPEG, PNG, and WebP images are allowed.")

        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024
        if file.size > max_size:
            raise ValidationError("File size must not exceed 5MB.")

        # Delete old profile picture if exists
        if user.profile_picture:
            user.profile_picture.delete(save=False)

        # Save new profile picture
        user.profile_picture.save(file.name, file, save=True)
        return user
