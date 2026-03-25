"""Tests for the Invitation model."""

import pytest

from apps.invitations.models import Invitation, InvitationStatus


@pytest.mark.django_db
class TestInvitationModel:
    def test_create_invitation(self, admin_user, receiver, org_with_admin):
        inv = Invitation.objects.create(
            organization=org_with_admin,
            sender=admin_user,
            receiver=receiver,
        )
        assert inv.pk is not None
        assert inv.status == InvitationStatus.PENDING
        assert inv.organization == org_with_admin
        assert inv.sender == admin_user
        assert inv.receiver == receiver
        assert str(inv) == "Invitation → receiver to Sunflower School (pending)"

    def test_unique_pending_per_user_org(self, admin_user, receiver, org_with_admin):
        from django.db import IntegrityError

        Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        with pytest.raises(IntegrityError):
            Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)

    def test_cascade_delete_org_deletes_invitations(self, admin_user, receiver, org_with_admin):
        Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        org_with_admin.delete()
        assert Invitation.objects.count() == 0


class TestInvitationModelStructure:
    def test_compound_indexes_exist(self):
        index_names = {idx.name for idx in Invitation._meta.indexes}
        assert "idx_invitation_receiver_status" in index_names
        assert "idx_invitation_org_status" in index_names
