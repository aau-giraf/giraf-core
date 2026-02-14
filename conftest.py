"""Shared test fixtures for GIRAF Core.

Provides common factories and helpers used across all test modules.
"""
import pytest
from django.test import Client

from apps.organizations.models import Membership, Organization, OrgRole
from apps.users.tests.factories import UserFactory


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def owner(db):
    return UserFactory(username="owner", password="testpass123")


@pytest.fixture
def admin_user(db):
    return UserFactory(username="admin", password="testpass123")


@pytest.fixture
def member(db):
    return UserFactory(username="member", password="testpass123")


@pytest.fixture
def non_member(db):
    return UserFactory(username="outsider", password="testpass123")


@pytest.fixture
def org(db, owner, member):
    """Organization with an owner and a member."""
    org = Organization.objects.create(name="Sunflower School")
    Membership.objects.create(user=owner, organization=org, role=OrgRole.OWNER)
    Membership.objects.create(user=member, organization=org, role=OrgRole.MEMBER)
    return org


@pytest.fixture
def second_org(db, non_member):
    """A second organization for cross-org tests."""
    org = Organization.objects.create(name="Other School")
    Membership.objects.create(user=non_member, organization=org, role=OrgRole.OWNER)
    return org


def auth_header(client: Client, username: str, password: str = "testpass123") -> dict:
    """Get JWT auth header for a user."""
    resp = client.post(
        "/api/v1/token/pair",
        data={"username": username, "password": password},
        content_type="application/json",
    )
    return {"HTTP_AUTHORIZATION": f"Bearer {resp.json()['access']}"}
