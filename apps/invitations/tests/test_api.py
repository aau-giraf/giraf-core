"""Tests for Invitation API endpoints."""

import pytest

from apps.invitations.models import Invitation, InvitationStatus
from apps.organizations.models import Membership, Organization, OrgRole
from conftest import auth_header_for_user


@pytest.mark.django_db
class TestSendInvitation:
    def test_admin_can_send_invitation(self, client, org_with_admin, admin_user, receiver):
        headers = auth_header_for_user(admin_user)
        response = client.post(
            f"/api/v1/organizations/{org_with_admin.id}/invitations",
            data={"receiver_email": "receiver@example.com"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["receiver_username"] == "receiver"
        assert body["organization_name"] == "Sunflower School"
        assert body["status"] == "pending"

    def test_member_cannot_send_invitation(self, client, org_with_admin, member, receiver):
        headers = auth_header_for_user(member)
        response = client.post(
            f"/api/v1/organizations/{org_with_admin.id}/invitations",
            data={"receiver_email": "receiver@example.com"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403

    def test_cannot_invite_nonexistent_email(self, client, org_with_admin, admin_user):
        headers = auth_header_for_user(admin_user)
        response = client.post(
            f"/api/v1/organizations/{org_with_admin.id}/invitations",
            data={"receiver_email": "nobody@example.com"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 400
        assert "Cannot send invitation" in response.json()["detail"]

    def test_cannot_invite_existing_member(self, client, org_with_admin, admin_user, member):
        headers = auth_header_for_user(admin_user)
        response = client.post(
            f"/api/v1/organizations/{org_with_admin.id}/invitations",
            data={"receiver_email": member.email},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 400
        assert "Cannot send invitation" in response.json()["detail"]

    def test_no_user_and_already_member_return_same_response(self, client, org_with_admin, admin_user, member):
        headers = auth_header_for_user(admin_user)
        resp_no_user = client.post(
            f"/api/v1/organizations/{org_with_admin.id}/invitations",
            data={"receiver_email": "nobody@example.com"},
            content_type="application/json",
            **headers,
        )
        resp_member = client.post(
            f"/api/v1/organizations/{org_with_admin.id}/invitations",
            data={"receiver_email": member.email},
            content_type="application/json",
            **headers,
        )
        assert resp_no_user.status_code == resp_member.status_code
        assert resp_no_user.json()["detail"] == resp_member.json()["detail"]

    def test_duplicate_pending_invitation_rejected(self, client, org_with_admin, admin_user, receiver):
        headers = auth_header_for_user(admin_user)
        client.post(
            f"/api/v1/organizations/{org_with_admin.id}/invitations",
            data={"receiver_email": "receiver@example.com"},
            content_type="application/json",
            **headers,
        )
        response = client.post(
            f"/api/v1/organizations/{org_with_admin.id}/invitations",
            data={"receiver_email": "receiver@example.com"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 409

    def test_invalid_email_format_rejected(self, client, org_with_admin, admin_user):
        headers = auth_header_for_user(admin_user)
        response = client.post(
            f"/api/v1/organizations/{org_with_admin.id}/invitations",
            data={"receiver_email": "not-an-email"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 422


@pytest.mark.django_db
class TestInvitationFlow:
    def test_receiver_sees_their_invitations(self, client, org_with_admin, admin_user, receiver):
        Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        headers = auth_header_for_user(receiver)
        response = client.get("/api/v1/invitations/received", **headers)
        assert response.status_code == 200
        body = response.json()["items"]
        assert len(body) == 1
        assert body[0]["organization_name"] == "Sunflower School"

    def test_admin_sees_org_invitations(self, client, org_with_admin, admin_user, receiver):
        Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        headers = auth_header_for_user(admin_user)
        response = client.get(f"/api/v1/organizations/{org_with_admin.id}/invitations", **headers)
        assert response.status_code == 200
        body = response.json()["items"]
        assert len(body) == 1

    def test_accept_invitation_creates_membership(self, client, org_with_admin, admin_user, receiver):
        inv = Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        headers = auth_header_for_user(receiver)
        response = client.post(
            f"/api/v1/invitations/{inv.id}/accept",
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        assert Membership.objects.filter(user=receiver, organization=org_with_admin, role=OrgRole.MEMBER).exists()
        inv.refresh_from_db()
        assert inv.status == InvitationStatus.ACCEPTED

    def test_reject_invitation(self, client, org_with_admin, admin_user, receiver):
        inv = Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        headers = auth_header_for_user(receiver)
        response = client.post(
            f"/api/v1/invitations/{inv.id}/reject",
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        inv.refresh_from_db()
        assert inv.status == InvitationStatus.REJECTED

    def test_only_receiver_can_respond(self, client, org_with_admin, admin_user, receiver):
        inv = Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        headers = auth_header_for_user(admin_user)
        response = client.post(
            f"/api/v1/invitations/{inv.id}/accept",
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403

    def test_admin_can_delete_org_invitation(self, client, org_with_admin, admin_user, receiver):
        inv = Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        headers = auth_header_for_user(admin_user)
        response = client.delete(
            f"/api/v1/organizations/{org_with_admin.id}/invitations/{inv.id}",
            **headers,
        )
        assert response.status_code == 204
        assert not Invitation.objects.filter(id=inv.id).exists()

    def test_cannot_accept_already_accepted_invitation(self, client, org_with_admin, admin_user, receiver):
        inv = Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        headers = auth_header_for_user(receiver)
        client.post(f"/api/v1/invitations/{inv.id}/accept", content_type="application/json", **headers)
        response = client.post(f"/api/v1/invitations/{inv.id}/accept", content_type="application/json", **headers)
        assert response.status_code == 400

    def test_cannot_accept_rejected_invitation(self, client, org_with_admin, admin_user, receiver):
        inv = Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        headers = auth_header_for_user(receiver)
        client.post(f"/api/v1/invitations/{inv.id}/reject", content_type="application/json", **headers)
        response = client.post(f"/api/v1/invitations/{inv.id}/accept", content_type="application/json", **headers)
        assert response.status_code == 400

    def test_cannot_reject_already_accepted_invitation(self, client, org_with_admin, admin_user, receiver):
        inv = Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        headers = auth_header_for_user(receiver)
        client.post(f"/api/v1/invitations/{inv.id}/accept", content_type="application/json", **headers)
        response = client.post(f"/api/v1/invitations/{inv.id}/reject", content_type="application/json", **headers)
        assert response.status_code == 400

    def test_member_cannot_list_org_invitations(self, client, org_with_admin, member):
        headers = auth_header_for_user(member)
        response = client.get(f"/api/v1/organizations/{org_with_admin.id}/invitations", **headers)
        assert response.status_code == 403

    def test_member_cannot_delete_org_invitation(self, client, org_with_admin, admin_user, member, receiver):
        inv = Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        headers = auth_header_for_user(member)
        response = client.delete(
            f"/api/v1/organizations/{org_with_admin.id}/invitations/{inv.id}",
            **headers,
        )
        assert response.status_code == 403

    def test_accept_nonexistent_invitation(self, client, receiver):
        headers = auth_header_for_user(receiver)
        response = client.post(
            "/api/v1/invitations/99999/accept",
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 404

    def test_reject_nonexistent_invitation(self, client, receiver):
        headers = auth_header_for_user(receiver)
        response = client.post(
            "/api/v1/invitations/99999/reject",
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 404

    def test_delete_invitation_from_wrong_org(self, client, org_with_admin, admin_user, receiver):
        inv = Invitation.objects.create(organization=org_with_admin, sender=admin_user, receiver=receiver)
        other_org = Organization.objects.create(name="Other School")
        from apps.organizations.models import Membership, OrgRole

        Membership.objects.create(user=admin_user, organization=other_org, role=OrgRole.ADMIN)
        headers = auth_header_for_user(admin_user)
        response = client.delete(
            f"/api/v1/organizations/{other_org.id}/invitations/{inv.id}",
            **headers,
        )
        assert response.status_code == 404
