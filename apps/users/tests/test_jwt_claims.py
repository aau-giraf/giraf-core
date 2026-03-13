"""Tests for JWT custom claims — org_roles embedded in access tokens.

Verifies that when a user logs in, their access token contains org_roles
as a dict mapping org_id → role string.
Written BEFORE implementation (TDD red phase).
"""

import pytest
from django.test import Client
from ninja_jwt.tokens import AccessToken

from apps.organizations.models import Membership, Organization, OrgRole
from apps.users.tests.factories import UserFactory


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    return UserFactory(username="jwtuser", password="testpass123")


@pytest.fixture
def orgs_with_roles(db, user):
    """Create 3 orgs where user has different roles."""
    org_a = Organization.objects.create(name="Org A")
    org_b = Organization.objects.create(name="Org B")
    org_c = Organization.objects.create(name="Org C")
    Membership.objects.create(user=user, organization=org_a, role=OrgRole.OWNER)
    Membership.objects.create(user=user, organization=org_b, role=OrgRole.ADMIN)
    Membership.objects.create(user=user, organization=org_c, role=OrgRole.MEMBER)
    return org_a, org_b, org_c


def login(client, username="jwtuser", password="testpass123"):
    resp = client.post(
        "/api/v1/token/pair",
        data={"username": username, "password": password},
        content_type="application/json",
    )
    return resp.json()


@pytest.mark.django_db
class TestJWTOrgRoleClaims:
    def test_access_token_contains_org_roles(self, client, user, orgs_with_roles):
        org_a, org_b, org_c = orgs_with_roles
        tokens = login(client)

        # Decode the access token and verify org_roles claim
        access = AccessToken(tokens["access"])
        org_roles = access["org_roles"]

        assert org_roles[str(org_a.id)] == "owner"
        assert org_roles[str(org_b.id)] == "admin"
        assert org_roles[str(org_c.id)] == "member"

    def test_user_id_claim(self, client, user):
        tokens = login(client)
        access = AccessToken(tokens["access"])
        assert access["user_id"] == user.id

    def test_user_with_no_orgs_has_empty_org_roles(self, client, user):
        tokens = login(client)
        access = AccessToken(tokens["access"])
        assert access["org_roles"] == {}

    def test_login_response_includes_org_roles(self, client, user, orgs_with_roles):
        """The /token/pair JSON response body also includes org_roles."""
        org_a, org_b, org_c = orgs_with_roles
        tokens = login(client)

        assert "org_roles" in tokens
        assert tokens["org_roles"][str(org_a.id)] == "owner"

    def test_org_roles_update_after_role_change(self, client, user, orgs_with_roles):
        """After a role change, a new token should reflect the updated role."""
        org_a, org_b, org_c = orgs_with_roles

        # Change user's role in org_b from admin to owner
        mem = Membership.objects.get(user=user, organization=org_b)
        mem.role = OrgRole.OWNER
        mem.save()

        tokens = login(client)
        access = AccessToken(tokens["access"])
        assert access["org_roles"][str(org_b.id)] == "owner"
