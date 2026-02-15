"""Invitation model.

Invitations let org admins invite users to join an organization.
Tracks status (pending → accepted/rejected) for auditing.
"""

from django.conf import settings
from django.db import models


class InvitationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"


class Invitation(models.Model):
    """An invitation for a user to join an organization."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_invitations",
    )
    status = models.CharField(
        max_length=10,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "invitations"
        # Only one pending invitation per user+org
        constraints = [
            models.UniqueConstraint(
                fields=["receiver", "organization"],
                condition=models.Q(status="pending"),
                name="unique_pending_invitation",
            ),
        ]
        indexes = [
            models.Index(fields=["receiver", "status"], name="idx_invitation_receiver_status"),
            models.Index(fields=["organization", "status"], name="idx_invitation_org_status"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Invitation → {self.receiver.username} to {self.organization.name} ({self.status})"
