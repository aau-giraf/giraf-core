"""Shared test fixtures for GIRAF Core.

Provides common factories and helpers used across all test modules.
"""

import pytest
from django.core.cache import cache
from django.test import Client
from ninja_jwt.tokens import AccessToken

from apps.organizations.models import Membership, Organization, OrgRole
from apps.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """Clear the cache before each test so rate limits don't leak across tests."""
    cache.clear()
    yield
    cache.clear()


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


def auth_header_for_user(user) -> dict:
    """Get JWT auth header by creating a token directly (no HTTP round-trip)."""
    token = AccessToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}


def auth_header(client: Client, username: str, password: str = "testpass123") -> dict:
    """Get JWT auth header for a user via HTTP (legacy helper)."""
    resp = client.post(
        "/api/v1/token/pair",
        data={"username": username, "password": password},
        content_type="application/json",
    )
    return {"HTTP_AUTHORIZATION": f"Bearer {resp.json()['access']}"}
