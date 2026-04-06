"""Custom User model for GIRAF Core.

Extends Django's AbstractUser with GIRAF-specific fields and behavior.
Users are caretakers, teachers, and staff at institutions serving kids with autism.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """GIRAF platform user (caretaker, teacher, staff)."""

    # AbstractUser already provides:
    #   username, first_name, last_name, email, password,
    #   is_staff, is_active, is_superuser, date_joined

    profile_picture = models.ImageField(
        upload_to="profile_pictures/%Y/%m/%d/",
        null=True,
        blank=True,
        help_text="User profile picture (max 20MB, JPEG/PNG/WebP)",
    )

    class Meta:
        db_table = "users"
        ordering = ["username"]

    @property
    def display_name(self) -> str:
        """Full name if available, otherwise username."""
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.username

    def __str__(self) -> str:
        return self.username
