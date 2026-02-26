"""Invitation business logic."""

import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.invitations.models import Invitation, InvitationStatus
from apps.organizations.models import Membership, OrgRole
from core.exceptions import BadRequestError, DuplicateInvitationError, InvitationSendError, ResourceNotFoundError

logger = logging.getLogger(__name__)

User = get_user_model()


class InvitationService:
    @staticmethod
    def _get_invitation_or_raise(invitation_id: int, *, for_update: bool = False) -> Invitation:
        qs = Invitation.objects.select_related("organization", "sender", "receiver")
        if for_update:
            qs = qs.select_for_update()
        try:
            return qs.get(id=invitation_id)
        except Invitation.DoesNotExist:
            raise ResourceNotFoundError(f"Invitation {invitation_id} not found.")

    @staticmethod
    def get_invitation(invitation_id: int) -> Invitation:
        return InvitationService._get_invitation_or_raise(invitation_id)

    @staticmethod
    @transaction.atomic
    def send(*, org_id: int, sender_id: int, receiver_email: str) -> Invitation:
        """Create an invitation.

        Raises:
            InvitationSendError: No user with that email or user is already a member.
            DuplicateInvitationError: A pending invitation already exists.
        """
        try:
            receiver = User.objects.get(email=receiver_email)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            raise InvitationSendError("Cannot send invitation.")

        if Membership.objects.filter(user=receiver, organization_id=org_id).exists():
            raise InvitationSendError("Cannot send invitation.")

        try:
            inv = Invitation.objects.create(
                organization_id=org_id,
                sender_id=sender_id,
                receiver=receiver,
            )
        except IntegrityError:
            raise DuplicateInvitationError("Pending invitation already exists.")

        logger.info("Invitation sent: id=%d org=%d sender=%d receiver=%d", inv.id, org_id, sender_id, receiver.id)
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
    def accept(*, invitation_id: int) -> Invitation:
        """Accept invitation: create membership, update status."""
        invitation = InvitationService._get_invitation_or_raise(invitation_id, for_update=True)
        if invitation.status != InvitationStatus.PENDING:
            raise BadRequestError("Invitation is no longer pending.")
        Membership.objects.get_or_create(
            user=invitation.receiver,
            organization=invitation.organization,
            defaults={"role": OrgRole.MEMBER},
        )
        invitation.status = InvitationStatus.ACCEPTED
        invitation.save(update_fields=["status"])
        logger.info(
            "Invitation accepted: id=%d user=%d org=%d",
            invitation.id,
            invitation.receiver_id,
            invitation.organization_id,
        )
        return invitation

    @staticmethod
    @transaction.atomic
    def reject(*, invitation_id: int) -> Invitation:
        invitation = InvitationService._get_invitation_or_raise(invitation_id, for_update=True)
        if invitation.status != InvitationStatus.PENDING:
            raise BadRequestError("Invitation is no longer pending.")
        invitation.status = InvitationStatus.REJECTED
        invitation.save(update_fields=["status"])
        logger.info("Invitation rejected: id=%d user=%d", invitation.id, invitation.receiver_id)
        return invitation

    @staticmethod
    def delete(*, invitation_id: int) -> None:
        invitation = InvitationService._get_invitation_or_raise(invitation_id)
        invitation.delete()
