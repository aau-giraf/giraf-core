"""Tests for Citizen model and API endpoints.

Citizens are kids with autism, belonging to an organization.
Written BEFORE implementation.
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
def member(db):
    return UserFactory(username="member", password="testpass123")


@pytest.fixture
def non_member(db):
    return UserFactory(username="outsider", password="testpass123")


@pytest.fixture
def org(db, owner, member):
    org = Organization.objects.create(name="Sunflower School")
    Membership.objects.create(user=owner, organization=org, role=OrgRole.OWNER)
    Membership.objects.create(user=member, organization=org, role=OrgRole.MEMBER)
    return org


def auth_header(client, username, password="testpass123"):
    resp = client.post(
        "/api/v1/token/pair",
        data={"username": username, "password": password},
        content_type="application/json",
    )
    return {"HTTP_AUTHORIZATION": f"Bearer {resp.json()['access']}"}


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCitizenModel:
    def test_create_citizen(self):
        from apps.citizens.models import Citizen

        org = Organization.objects.create(name="Test School")
        citizen = Citizen.objects.create(
            first_name="Alice",
            last_name="Smith",
            organization=org,
        )
        assert citizen.pk is not None
        assert citizen.first_name == "Alice"
        assert citizen.organization == org
        assert str(citizen) == "Alice Smith"

    def test_citizen_belongs_to_organization(self):
        from apps.citizens.models import Citizen

        org = Organization.objects.create(name="Test School")
        Citizen.objects.create(first_name="Bob", last_name="Jones", organization=org)
        assert org.citizens.count() == 1

    def test_cascade_delete_org_deletes_citizens(self):
        from apps.citizens.models import Citizen

        org = Organization.objects.create(name="Test School")
        Citizen.objects.create(first_name="Bob", last_name="Jones", organization=org)
        org.delete()
        assert Citizen.objects.count() == 0


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateCitizen:
    def test_member_can_create_citizen(self, client, org, member):
        headers = auth_header(client, "member")
        response = client.post(
            f"/api/v1/organizations/{org.id}/citizens",
            data={"first_name": "Alice", "last_name": "Smith"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "Alice"
        assert data["last_name"] == "Smith"

    def test_non_member_cannot_create_citizen(self, client, org, non_member):
        headers = auth_header(client, "outsider")
        response = client.post(
            f"/api/v1/organizations/{org.id}/citizens",
            data={"first_name": "Alice", "last_name": "Smith"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestListCitizens:
    def test_list_citizens_in_org(self, client, org, member):
        from apps.citizens.models import Citizen

        Citizen.objects.create(first_name="Alice", last_name="A", organization=org)
        Citizen.objects.create(first_name="Bob", last_name="B", organization=org)

        headers = auth_header(client, "member")
        response = client.get(f"/api/v1/organizations/{org.id}/citizens", **headers)
        assert response.status_code == 200
        assert len(response.json()["items"]) == 2

    def test_non_member_cannot_list(self, client, org, non_member):
        headers = auth_header(client, "outsider")
        response = client.get(f"/api/v1/organizations/{org.id}/citizens", **headers)
        assert response.status_code == 403


@pytest.mark.django_db
class TestGetCitizen:
    def test_get_citizen_detail(self, client, org, member):
        from apps.citizens.models import Citizen

        citizen = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)

        headers = auth_header(client, "member")
        response = client.get(f"/api/v1/citizens/{citizen.id}", **headers)
        assert response.status_code == 200
        assert response.json()["first_name"] == "Alice"

    def test_non_member_cannot_get_citizen(self, client, org, non_member):
        from apps.citizens.models import Citizen

        citizen = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)

        headers = auth_header(client, "outsider")
        response = client.get(f"/api/v1/citizens/{citizen.id}", **headers)
        assert response.status_code == 403


@pytest.mark.django_db
class TestUpdateCitizen:
    def test_member_can_update_citizen(self, client, org, member):
        from apps.citizens.models import Citizen

        citizen = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)

        headers = auth_header(client, "member")
        response = client.patch(
            f"/api/v1/citizens/{citizen.id}",
            data={"first_name": "Alicia"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        assert response.json()["first_name"] == "Alicia"


@pytest.mark.django_db
class TestDeleteCitizen:
    def test_admin_can_delete_citizen(self, client, org, owner):
        from apps.citizens.models import Citizen

        citizen = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)

        headers = auth_header(client, "owner")
        response = client.delete(f"/api/v1/citizens/{citizen.id}", **headers)
        assert response.status_code == 204
        assert not Citizen.objects.filter(id=citizen.id).exists()

    def test_member_cannot_delete_citizen(self, client, org, member):
        from apps.citizens.models import Citizen

        citizen = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)

        headers = auth_header(client, "member")
        response = client.delete(f"/api/v1/citizens/{citizen.id}", **headers)
        assert response.status_code == 403
