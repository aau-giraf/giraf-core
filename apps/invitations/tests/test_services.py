"""Tests for InvitationService."""

import pytest

from apps.invitations.services import InvitationService
from core.exceptions import DuplicateInvitationError, InvitationSendError


@pytest.mark.django_db
class TestInvitationService:
    def test_send_raises_on_nonexistent_email(self, admin_user, org_with_admin):
        with pytest.raises(InvitationSendError):
            InvitationService.send(
                org_id=org_with_admin.id,
                sender_id=admin_user.id,
                receiver_email="nobody@example.com",
            )

    def test_send_raises_on_already_member(self, admin_user, org_with_admin, member):
        with pytest.raises(InvitationSendError):
            InvitationService.send(
                org_id=org_with_admin.id,
                sender_id=admin_user.id,
                receiver_email=member.email,
            )

    def test_send_raises_on_duplicate(self, admin_user, receiver, org_with_admin):
        InvitationService.send(
            org_id=org_with_admin.id,
            sender_id=admin_user.id,
            receiver_email="receiver@example.com",
        )
        with pytest.raises(DuplicateInvitationError):
            InvitationService.send(
                org_id=org_with_admin.id,
                sender_id=admin_user.id,
                receiver_email="receiver@example.com",
            )
