"""Tests for rate-limiting throttle classes."""

import pytest
from django.test import Client

from apps.users.tests.factories import UserFactory


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
class TestLoginRateThrottle:
    def test_login_blocks_after_limit(self, client):
        UserFactory(username="throttleuser", password="testpass123")

        for _ in range(5):
            resp = client.post(
                "/api/v1/token/pair",
                data={"username": "throttleuser", "password": "testpass123"},
                content_type="application/json",
            )
            assert resp.status_code == 200

        # 6th attempt should be throttled
        resp = client.post(
            "/api/v1/token/pair",
            data={"username": "throttleuser", "password": "testpass123"},
            content_type="application/json",
        )
        assert resp.status_code == 429


@pytest.mark.django_db
class TestRegisterRateThrottle:
    def test_register_blocks_after_limit(self, client):
        for i in range(3):
            resp = client.post(
                "/api/v1/auth/register",
                data={
                    "username": f"reguser{i}",
                    "password": "StrongP@ss123!",
                    "email": f"reg{i}@example.com",
                },
                content_type="application/json",
            )
            assert resp.status_code == 201

        # 4th attempt should be throttled
        resp = client.post(
            "/api/v1/auth/register",
            data={
                "username": "reguser3",
                "password": "StrongP@ss123!",
                "email": "reg3@example.com",
            },
            content_type="application/json",
        )
        assert resp.status_code == 429


@pytest.mark.django_db
class TestInvitationSendRateThrottle:
    def test_invitation_send_blocks_after_limit(self, client):
        from apps.organizations.models import Membership, Organization, OrgRole

        admin = UserFactory(username="invadmin", password="testpass123")
        org = Organization.objects.create(name="Throttle Org")
        Membership.objects.create(user=admin, organization=org, role=OrgRole.OWNER)

        # Create receivers
        receivers = []
        for i in range(11):
            u = UserFactory(username=f"receiver{i}", email=f"recv{i}@example.com")
            receivers.append(u)

        # Get auth token
        token_resp = client.post(
            "/api/v1/token/pair",
            data={"username": "invadmin", "password": "testpass123"},
            content_type="application/json",
        )
        access = token_resp.json()["access"]
        headers = {"HTTP_AUTHORIZATION": f"Bearer {access}"}

        for i in range(10):
            resp = client.post(
                f"/api/v1/organizations/{org.id}/invitations",
                data={"receiver_email": f"recv{i}@example.com"},
                content_type="application/json",
                **headers,
            )
            assert resp.status_code in (201, 400, 409), f"Request {i} got {resp.status_code}"

        # 11th attempt should be throttled
        resp = client.post(
            f"/api/v1/organizations/{org.id}/invitations",
            data={"receiver_email": "recv10@example.com"},
            content_type="application/json",
            **headers,
        )
        assert resp.status_code == 429
