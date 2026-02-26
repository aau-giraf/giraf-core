"""Organization and Membership models.

Organizations represent schools/institutions. Membership is the explicit
through-table linking users to organizations with role-based access.
"""

from django.conf import settings
from django.db import models


class OrgRole(models.TextChoices):
    MEMBER = "member", "Member"
    ADMIN = "admin", "Admin"
    OWNER = "owner", "Owner"


class Organization(models.Model):
    """A school or institution serving kids with autism."""

    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.name or not self.name.strip():
            raise ValidationError({"name": "Organization name is required."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Membership(models.Model):
    """Links a user to an organization with a specific role."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=10,
        choices=OrgRole.choices,
        default=OrgRole.MEMBER,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "memberships"
        constraints = [
            models.UniqueConstraint(fields=["user", "organization"], name="unique_membership"),
        ]
        ordering = ["organization", "user"]

    def __str__(self) -> str:
        return f"{self.user.username} @ {self.organization.name} ({self.role})"

    _ROLE_LEVEL: dict[str, int] = {OrgRole.MEMBER: 0, OrgRole.ADMIN: 1, OrgRole.OWNER: 2}

    @property
    def _role_level(self) -> int:
        return self._ROLE_LEVEL.get(self.role, 0)

    @property
    def is_member(self) -> bool:
        return self._role_level >= self._ROLE_LEVEL[OrgRole.MEMBER]

    @property
    def is_admin(self) -> bool:
        return self._role_level >= self._ROLE_LEVEL[OrgRole.ADMIN]

    @property
    def is_owner(self) -> bool:
        return self._role_level >= self._ROLE_LEVEL[OrgRole.OWNER]
