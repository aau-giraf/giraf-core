"""Invitation business logic."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.invitations.models import Invitation, InvitationStatus
from apps.organizations.models import Membership, OrgRole
from core.exceptions import BadRequestError, DuplicateInvitationError, InvitationSendError

User = get_user_model()


class InvitationService:
    @staticmethod
    @transaction.atomic
    def send(*, organization, sender, receiver_email: str) -> Invitation:
        """Create an invitation.

        Raises:
            InvitationSendError: No user with that email or user is already a member.
            DuplicateInvitationError: A pending invitation already exists.
        """
        try:
            receiver = User.objects.get(email=receiver_email)
        except User.DoesNotExist:
            raise InvitationSendError("Cannot send invitation.")

        if Membership.objects.filter(user=receiver, organization=organization).exists():
            raise InvitationSendError("Cannot send invitation.")

        try:
            inv = Invitation.objects.create(
                organization=organization,
                sender=sender,
                receiver=receiver,
            )
        except IntegrityError:
            raise DuplicateInvitationError("Pending invitation already exists.")

        return Invitation.objects.select_related("organization", "sender", "receiver").get(id=inv.id)

    @staticmethod
    def list_received(user):
        return Invitation.objects.filter(receiver=user, status=InvitationStatus.PENDING).select_related(
            "organization", "sender", "receiver"
        )

    @staticmethod
    def list_for_org(organization_id: int):
        return Invitation.objects.filter(
            organization_id=organization_id,
            status=InvitationStatus.PENDING,
        ).select_related("organization", "sender", "receiver")

    @staticmethod
    @transaction.atomic
    def accept(invitation: Invitation) -> None:
        """Accept invitation: create membership, update status."""
        if invitation.status != InvitationStatus.PENDING:
            raise BadRequestError("Invitation is no longer pending.")
        Membership.objects.get_or_create(
            user=invitation.receiver,
            organization=invitation.organization,
            defaults={"role": OrgRole.MEMBER},
        )
        invitation.status = InvitationStatus.ACCEPTED
        invitation.save(update_fields=["status"])

    @staticmethod
    def reject(invitation: Invitation) -> None:
        if invitation.status != InvitationStatus.PENDING:
            raise BadRequestError("Invitation is no longer pending.")
        invitation.status = InvitationStatus.REJECTED
        invitation.save(update_fields=["status"])

    @staticmethod
    def delete(invitation: Invitation) -> None:
        invitation.delete()
