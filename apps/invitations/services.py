"""Invitation business logic."""
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.invitations.models import Invitation, InvitationStatus
from apps.organizations.models import Membership, OrgRole
from core.exceptions import AlreadyMemberError, DuplicateInvitationError, ReceiverNotFoundError

User = get_user_model()


class InvitationService:
    @staticmethod
    def send(*, organization, sender, receiver_email: str) -> Invitation:
        """Create an invitation.

        Raises:
            ReceiverNotFoundError: No user with that email.
            AlreadyMemberError: User is already a member of the org.
            DuplicateInvitationError: A pending invitation already exists.
        """
        try:
            receiver = User.objects.get(email=receiver_email)
        except User.DoesNotExist:
            raise ReceiverNotFoundError("No user with that email.")

        if Membership.objects.filter(
            user=receiver, organization=organization
        ).exists():
            raise AlreadyMemberError("User is already a member.")

        try:
            inv = Invitation.objects.create(
                organization=organization,
                sender=sender,
                receiver=receiver,
            )
        except IntegrityError:
            raise DuplicateInvitationError("Pending invitation already exists.")

        return inv

    @staticmethod
    def list_received(user):
        return Invitation.objects.filter(
            receiver=user, status=InvitationStatus.PENDING
        ).select_related("organization", "sender", "receiver")

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
        Membership.objects.get_or_create(
            user=invitation.receiver,
            organization=invitation.organization,
            defaults={"role": OrgRole.MEMBER},
        )
        invitation.status = InvitationStatus.ACCEPTED
        invitation.save(update_fields=["status"])

    @staticmethod
    def reject(invitation: Invitation) -> None:
        invitation.status = InvitationStatus.REJECTED
        invitation.save(update_fields=["status"])

    @staticmethod
    def delete(invitation: Invitation) -> None:
        invitation.delete()
