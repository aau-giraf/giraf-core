"""Tests for Invitation model and API endpoints.

Invitations let org admins invite users to join an organization.
"""
import pytest

from apps.invitations.models import Invitation, InvitationStatus
from apps.invitations.services import InvitationService
from apps.organizations.models import Membership, Organization, OrgRole
from apps.users.tests.factories import UserFactory
from conftest import auth_header
from core.exceptions import AlreadyMemberError, DuplicateInvitationError, ReceiverNotFoundError


@pytest.fixture
def admin_user(db):
    return UserFactory(username="admin", password="testpass123")


@pytest.fixture
def receiver(db):
    return UserFactory(
        username="receiver",
        email="receiver@example.com",
        password="testpass123",
    )


@pytest.fixture
def org(db, admin_user, member):
    org = Organization.objects.create(name="Sunflower School")
    Membership.objects.create(user=admin_user, organization=org, role=OrgRole.ADMIN)
    Membership.objects.create(user=member, organization=org, role=OrgRole.MEMBER)
    return org


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInvitationModel:
    def test_create_invitation(self, admin_user, receiver, org):
        inv = Invitation.objects.create(
            organization=org,
            sender=admin_user,
            receiver=receiver,
        )
        assert inv.pk is not None
        assert inv.status == InvitationStatus.PENDING
        assert inv.organization == org
        assert inv.sender == admin_user
        assert inv.receiver == receiver
        assert str(inv) == "Invitation → receiver to Sunflower School (pending)"

    def test_unique_pending_per_user_org(self, admin_user, receiver, org):
        """Cannot create two pending invitations for the same user+org."""
        from django.db import IntegrityError

        Invitation.objects.create(
            organization=org, sender=admin_user, receiver=receiver
        )
        with pytest.raises(IntegrityError):
            Invitation.objects.create(
                organization=org, sender=admin_user, receiver=receiver
            )

    def test_cascade_delete_org_deletes_invitations(self, admin_user, receiver, org):
        Invitation.objects.create(
            organization=org, sender=admin_user, receiver=receiver
        )
        org.delete()
        assert Invitation.objects.count() == 0


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInvitationService:
    def test_send_raises_on_nonexistent_email(self, admin_user, org):
        with pytest.raises(ReceiverNotFoundError):
            InvitationService.send(
                organization=org,
                sender=admin_user,
                receiver_email="nobody@example.com",
            )

    def test_send_raises_on_already_member(self, admin_user, org, member):
        with pytest.raises(AlreadyMemberError):
            InvitationService.send(
                organization=org,
                sender=admin_user,
                receiver_email=member.email,
            )

    def test_send_raises_on_duplicate(self, admin_user, receiver, org):
        InvitationService.send(
            organization=org,
            sender=admin_user,
            receiver_email="receiver@example.com",
        )
        with pytest.raises(DuplicateInvitationError):
            InvitationService.send(
                organization=org,
                sender=admin_user,
                receiver_email="receiver@example.com",
            )


# ---------------------------------------------------------------------------
# API tests — Send invitation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSendInvitation:
    def test_admin_can_send_invitation(self, client, org, admin_user, receiver):
        headers = auth_header(client, "admin")
        response = client.post(
            f"/api/v1/organizations/{org.id}/invitations",
            data={"receiver_email": "receiver@example.com"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["receiver_username"] == "receiver"
        assert body["organization_name"] == "Sunflower School"
        assert body["status"] == "pending"

    def test_member_cannot_send_invitation(self, client, org, member, receiver):
        headers = auth_header(client, "member")
        response = client.post(
            f"/api/v1/organizations/{org.id}/invitations",
            data={"receiver_email": "receiver@example.com"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403

    def test_cannot_invite_nonexistent_email(self, client, org, admin_user):
        """Returns generic 400 to prevent email enumeration."""
        headers = auth_header(client, "admin")
        response = client.post(
            f"/api/v1/organizations/{org.id}/invitations",
            data={"receiver_email": "nobody@example.com"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 400
        assert "Cannot send invitation" in response.json()["detail"]

    def test_cannot_invite_existing_member(self, client, org, admin_user, member):
        """Returns same generic 400 as nonexistent — no enumeration leak."""
        headers = auth_header(client, "admin")
        response = client.post(
            f"/api/v1/organizations/{org.id}/invitations",
            data={"receiver_email": member.email},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 400
        assert "Cannot send invitation" in response.json()["detail"]

    def test_no_user_and_already_member_return_same_response(
        self, client, org, admin_user, member
    ):
        """Both no_user and already_member produce identical error responses."""
        headers = auth_header(client, "admin")
        resp_no_user = client.post(
            f"/api/v1/organizations/{org.id}/invitations",
            data={"receiver_email": "nobody@example.com"},
            content_type="application/json",
            **headers,
        )
        resp_member = client.post(
            f"/api/v1/organizations/{org.id}/invitations",
            data={"receiver_email": member.email},
            content_type="application/json",
            **headers,
        )
        assert resp_no_user.status_code == resp_member.status_code
        assert resp_no_user.json()["detail"] == resp_member.json()["detail"]

    def test_duplicate_pending_invitation_rejected(
        self, client, org, admin_user, receiver
    ):
        headers = auth_header(client, "admin")
        client.post(
            f"/api/v1/organizations/{org.id}/invitations",
            data={"receiver_email": "receiver@example.com"},
            content_type="application/json",
            **headers,
        )
        response = client.post(
            f"/api/v1/organizations/{org.id}/invitations",
            data={"receiver_email": "receiver@example.com"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 409

    def test_invalid_email_format_rejected(self, client, org, admin_user):
        """Email validation should reject malformed emails."""
        headers = auth_header(client, "admin")
        response = client.post(
            f"/api/v1/organizations/{org.id}/invitations",
            data={"receiver_email": "not-an-email"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# API tests — List & respond
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInvitationFlow:
    def test_receiver_sees_their_invitations(self, client, org, admin_user, receiver):
        Invitation.objects.create(
            organization=org, sender=admin_user, receiver=receiver
        )
        headers = auth_header(client, "receiver")
        response = client.get("/api/v1/invitations/received", **headers)
        assert response.status_code == 200
        body = response.json()["items"]
        assert len(body) == 1
        assert body[0]["organization_name"] == "Sunflower School"

    def test_admin_sees_org_invitations(self, client, org, admin_user, receiver):
        Invitation.objects.create(
            organization=org, sender=admin_user, receiver=receiver
        )
        headers = auth_header(client, "admin")
        response = client.get(
            f"/api/v1/organizations/{org.id}/invitations", **headers
        )
        assert response.status_code == 200
        body = response.json()["items"]
        assert len(body) == 1

    def test_accept_invitation_creates_membership(
        self, client, org, admin_user, receiver
    ):
        inv = Invitation.objects.create(
            organization=org, sender=admin_user, receiver=receiver
        )
        headers = auth_header(client, "receiver")
        response = client.post(
            f"/api/v1/invitations/{inv.id}/accept",
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        assert Membership.objects.filter(
            user=receiver, organization=org, role=OrgRole.MEMBER
        ).exists()
        inv.refresh_from_db()
        assert inv.status == InvitationStatus.ACCEPTED

    def test_reject_invitation(self, client, org, admin_user, receiver):
        inv = Invitation.objects.create(
            organization=org, sender=admin_user, receiver=receiver
        )
        headers = auth_header(client, "receiver")
        response = client.post(
            f"/api/v1/invitations/{inv.id}/reject",
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        inv.refresh_from_db()
        assert inv.status == InvitationStatus.REJECTED

    def test_only_receiver_can_respond(self, client, org, admin_user, receiver):
        inv = Invitation.objects.create(
            organization=org, sender=admin_user, receiver=receiver
        )
        headers = auth_header(client, "admin")
        response = client.post(
            f"/api/v1/invitations/{inv.id}/accept",
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403

    def test_admin_can_delete_org_invitation(self, client, org, admin_user, receiver):
        inv = Invitation.objects.create(
            organization=org, sender=admin_user, receiver=receiver
        )
        headers = auth_header(client, "admin")
        response = client.delete(
            f"/api/v1/organizations/{org.id}/invitations/{inv.id}",
            **headers,
        )
        assert response.status_code == 204
        assert not Invitation.objects.filter(id=inv.id).exists()
