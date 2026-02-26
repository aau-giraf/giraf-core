"""Business logic for user operations.

All business logic lives here — never in API endpoints.
"""

import logging
import mimetypes
import uuid

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from apps.users.models import User
from core.exceptions import BusinessValidationError, ConflictError, ResourceNotFoundError
from core.validators import validate_image_upload

logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    def _get_user_or_raise(user_id: int) -> User:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ResourceNotFoundError(f"User {user_id} not found.")

    @staticmethod
    @transaction.atomic
    def register(
        *, username: str, password: str, email: str | None = None, first_name: str = "", last_name: str = ""
    ) -> User:
        """Create a new user with validated password.

        Raises:
            ConflictError: If username already exists.
            BusinessValidationError: If password doesn't meet strength requirements.
        """
        if User.objects.filter(username=username).exists():
            raise ConflictError(f"Username '{username}' is already taken.")

        # Validate password strength using Django's validators
        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise BusinessValidationError(e.messages)

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email or "",
            first_name=first_name,
            last_name=last_name,
        )
        logger.info("User registered: id=%d username=%s", user.id, user.username)
        return user

    @staticmethod
    @transaction.atomic
    def update_user(
        *, user_id: int, first_name: str | None = None, last_name: str | None = None, email: str | None = None
    ) -> User:
        """Update user profile fields. Only updates non-None values."""
        user = UserService._get_user_or_raise(user_id)
        updated_fields: list[str] = []
        if first_name is not None:
            user.first_name = first_name
            updated_fields.append("first_name")
        if last_name is not None:
            user.last_name = last_name
            updated_fields.append("last_name")
        if email is not None:
            if User.objects.filter(email=email).exclude(id=user_id).exists():
                raise ConflictError("A user with this email already exists.")
            user.email = email
            updated_fields.append("email")
        if updated_fields:
            user.save(update_fields=updated_fields)
        return user

    @staticmethod
    @transaction.atomic
    def change_password(*, user_id: int, old_password: str, new_password: str) -> User:
        """Change user password with validation.

        Raises:
            BusinessValidationError: If old password is incorrect or new password is weak.
        """
        user = UserService._get_user_or_raise(user_id)
        if not user.check_password(old_password):
            raise BusinessValidationError("Old password is incorrect.")

        # Django's built-in password validators (min length 8, etc.)
        try:
            validate_password(new_password)
        except DjangoValidationError as e:
            raise BusinessValidationError(e.messages)

        user.set_password(new_password)
        user.save()
        return user

    @staticmethod
    @transaction.atomic
    def delete_user(*, user_id: int) -> None:
        """Deactivate user account (soft delete)."""
        user = UserService._get_user_or_raise(user_id)
        user.is_active = False
        user.save(update_fields=["is_active"])
        logger.info("User deactivated: id=%d username=%s", user.id, user.username)

    @staticmethod
    @transaction.atomic
    def upload_profile_picture(*, user_id: int, file) -> User:
        """Upload and validate profile picture.

        Raises:
            BusinessValidationError: If file type or size is invalid.
        """
        user = UserService._get_user_or_raise(user_id)
        mime_type = validate_image_upload(file)

        # Delete old profile picture if exists
        if user.profile_picture:
            user.profile_picture.delete(save=False)

        # Save new profile picture with sanitized filename
        ext = mimetypes.guess_extension(mime_type) or ".bin"
        safe_name = f"{uuid.uuid4().hex}{ext}"
        user.profile_picture.save(safe_name, file, save=True)
        return user
