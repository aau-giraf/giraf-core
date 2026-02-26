"""Tests for Organization API endpoints."""

import pytest

from apps.organizations.models import Membership, Organization, OrgRole
from apps.users.tests.factories import UserFactory
from conftest import auth_header


@pytest.fixture
def user(db):
    return UserFactory(username="testuser", password="testpass123")


@pytest.fixture
def other_user(db):
    return UserFactory(username="otheruser", password="testpass123")


@pytest.mark.django_db
class TestCreateOrganization:
    def test_create_org_returns_201(self, client, user):
        headers = auth_header(client, "testuser")
        response = client.post(
            "/api/v1/organizations",
            data={"name": "Sunflower School"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Sunflower School"
        assert data["id"] is not None

    def test_creator_becomes_owner(self, client, user):
        headers = auth_header(client, "testuser")
        response = client.post(
            "/api/v1/organizations",
            data={"name": "Sunflower School"},
            content_type="application/json",
            **headers,
        )
        org_id = response.json()["id"]
        membership = Membership.objects.get(user=user, organization_id=org_id)
        assert membership.role == OrgRole.OWNER

    def test_create_org_unauthenticated(self, client):
        response = client.post(
            "/api/v1/organizations",
            data={"name": "Test School"},
            content_type="application/json",
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestListOrganizations:
    def test_list_returns_user_orgs(self, client, user, other_user):
        headers = auth_header(client, "testuser")
        org1 = Organization.objects.create(name="School A")
        org2 = Organization.objects.create(name="School B")
        org3 = Organization.objects.create(name="School C")
        Membership.objects.create(user=user, organization=org1, role=OrgRole.MEMBER)
        Membership.objects.create(user=user, organization=org2, role=OrgRole.OWNER)
        Membership.objects.create(user=other_user, organization=org3, role=OrgRole.MEMBER)

        response = client.get("/api/v1/organizations", **headers)
        assert response.status_code == 200
        data = response.json()["items"]
        org_names = [o["name"] for o in data]
        assert "School A" in org_names
        assert "School B" in org_names
        assert "School C" not in org_names  # other_user's org

    def test_list_empty_when_no_memberships(self, client, user):
        headers = auth_header(client, "testuser")
        response = client.get("/api/v1/organizations", **headers)
        assert response.status_code == 200
        assert response.json()["items"] == []


@pytest.mark.django_db
class TestGetOrganization:
    def test_get_org_detail(self, client, user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.MEMBER)

        response = client.get(f"/api/v1/organizations/{org.id}", **headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Test School"

    def test_get_org_non_member_returns_403(self, client, user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Secret School")

        response = client.get(f"/api/v1/organizations/{org.id}", **headers)
        assert response.status_code == 403

    def test_get_org_not_found(self, client, user):
        headers = auth_header(client, "testuser")
        response = client.get("/api/v1/organizations/99999", **headers)
        assert response.status_code == 403


@pytest.mark.django_db
class TestListMembers:
    def test_list_members_of_org(self, client, user, other_user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)
        Membership.objects.create(user=other_user, organization=org, role=OrgRole.MEMBER)

        response = client.get(f"/api/v1/organizations/{org.id}/members", **headers)
        assert response.status_code == 200
        data = response.json()["items"]
        assert len(data) == 2

    def test_list_members_non_member_returns_403(self, client, user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Secret School")

        response = client.get(f"/api/v1/organizations/{org.id}/members", **headers)
        assert response.status_code == 403


@pytest.mark.django_db
class TestUpdateMemberRole:
    def test_owner_can_change_role(self, client, user, other_user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)
        Membership.objects.create(user=other_user, organization=org, role=OrgRole.MEMBER)

        response = client.patch(
            f"/api/v1/organizations/{org.id}/members/{other_user.id}",
            data={"role": "admin"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        other_user_membership = Membership.objects.get(user=other_user, organization=org)
        assert other_user_membership.role == OrgRole.ADMIN

    def test_non_owner_cannot_change_role(self, client, user, other_user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.ADMIN)
        Membership.objects.create(user=other_user, organization=org, role=OrgRole.MEMBER)

        response = client.patch(
            f"/api/v1/organizations/{org.id}/members/{other_user.id}",
            data={"role": "admin"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403

    def test_invalid_role_returns_400(self, client, user, other_user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)
        Membership.objects.create(user=other_user, organization=org, role=OrgRole.MEMBER)

        response = client.patch(
            f"/api/v1/organizations/{org.id}/members/{other_user.id}",
            data={"role": "superadmin"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 422

    def test_cannot_demote_last_owner(self, client, user, other_user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)
        Membership.objects.create(user=other_user, organization=org, role=OrgRole.MEMBER)

        response = client.patch(
            f"/api/v1/organizations/{org.id}/members/{user.id}",
            data={"role": "member"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestUpdateOrganization:
    def test_owner_can_update(self, client, user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Old Name")
        Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)

        response = client.patch(
            f"/api/v1/organizations/{org.id}",
            data={"name": "New Name"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_non_owner_cannot_update(self, client, user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Old Name")
        Membership.objects.create(user=user, organization=org, role=OrgRole.ADMIN)

        response = client.patch(
            f"/api/v1/organizations/{org.id}",
            data={"name": "New Name"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestDeleteOrganization:
    def test_owner_can_delete(self, client, user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Doomed School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)

        response = client.delete(f"/api/v1/organizations/{org.id}", **headers)
        assert response.status_code == 204
        assert not Organization.objects.filter(id=org.id).exists()

    def test_non_owner_cannot_delete(self, client, user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Safe School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.ADMIN)

        response = client.delete(f"/api/v1/organizations/{org.id}", **headers)
        assert response.status_code == 403


@pytest.mark.django_db
class TestUpdateMemberRoleErrors:
    def test_update_role_nonexistent_member_returns_404(self, client, user, other_user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)

        response = client.patch(
            f"/api/v1/organizations/{org.id}/members/99999",
            data={"role": "admin"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestRemoveMember:
    def test_owner_can_remove_member(self, client, user, other_user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)
        Membership.objects.create(user=other_user, organization=org, role=OrgRole.MEMBER)

        response = client.delete(
            f"/api/v1/organizations/{org.id}/members/{other_user.id}",
            **headers,
        )
        assert response.status_code == 204
        assert not Membership.objects.filter(user=other_user, organization=org).exists()

    def test_admin_can_remove_member(self, client, user, other_user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.ADMIN)
        Membership.objects.create(user=other_user, organization=org, role=OrgRole.MEMBER)

        response = client.delete(
            f"/api/v1/organizations/{org.id}/members/{other_user.id}",
            **headers,
        )
        assert response.status_code == 204

    def test_member_cannot_remove_other_member(self, client, user, other_user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.MEMBER)
        Membership.objects.create(user=other_user, organization=org, role=OrgRole.MEMBER)

        response = client.delete(
            f"/api/v1/organizations/{org.id}/members/{other_user.id}",
            **headers,
        )
        assert response.status_code == 403

    def test_cannot_remove_last_owner(self, client, user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)

        response = client.delete(
            f"/api/v1/organizations/{org.id}/members/{user.id}",
            **headers,
        )
        assert response.status_code == 400

    def test_remove_nonexistent_member_returns_404(self, client, user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)

        response = client.delete(
            f"/api/v1/organizations/{org.id}/members/99999",
            **headers,
        )
        assert response.status_code == 404

    def test_can_remove_owner_when_multiple_owners(self, client, user, other_user):
        headers = auth_header(client, "testuser")
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)
        Membership.objects.create(user=other_user, organization=org, role=OrgRole.OWNER)

        response = client.delete(
            f"/api/v1/organizations/{org.id}/members/{other_user.id}",
            **headers,
        )
        assert response.status_code == 204
        assert not Membership.objects.filter(user=other_user, organization=org).exists()
