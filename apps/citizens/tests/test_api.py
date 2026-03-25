"""Tests for Citizen API endpoints."""

import pytest

from conftest import auth_header_for_user


@pytest.mark.django_db
class TestCreateCitizen:
    def test_member_can_create_citizen(self, client, org, member):
        headers = auth_header_for_user(member)
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
        headers = auth_header_for_user(non_member)
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

        headers = auth_header_for_user(member)
        response = client.get(f"/api/v1/organizations/{org.id}/citizens", **headers)
        assert response.status_code == 200
        assert len(response.json()["items"]) == 2

    def test_non_member_cannot_list(self, client, org, non_member):
        headers = auth_header_for_user(non_member)
        response = client.get(f"/api/v1/organizations/{org.id}/citizens", **headers)
        assert response.status_code == 403


@pytest.mark.django_db
class TestGetCitizen:
    def test_get_citizen_detail(self, client, org, member):
        from apps.citizens.models import Citizen

        citizen = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)

        headers = auth_header_for_user(member)
        response = client.get(f"/api/v1/citizens/{citizen.id}", **headers)
        assert response.status_code == 200
        assert response.json()["first_name"] == "Alice"

    def test_non_member_cannot_get_citizen(self, client, org, non_member):
        from apps.citizens.models import Citizen

        citizen = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)

        headers = auth_header_for_user(non_member)
        response = client.get(f"/api/v1/citizens/{citizen.id}", **headers)
        assert response.status_code == 403


@pytest.mark.django_db
class TestUpdateCitizen:
    def test_member_can_update_citizen(self, client, org, member):
        from apps.citizens.models import Citizen

        citizen = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)

        headers = auth_header_for_user(member)
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

        headers = auth_header_for_user(owner)
        response = client.delete(f"/api/v1/citizens/{citizen.id}", **headers)
        assert response.status_code == 204
        assert not Citizen.objects.filter(id=citizen.id).exists()

    def test_member_cannot_delete_citizen(self, client, org, member):
        from apps.citizens.models import Citizen

        citizen = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)

        headers = auth_header_for_user(member)
        response = client.delete(f"/api/v1/citizens/{citizen.id}", **headers)
        assert response.status_code == 403

    def test_delete_nonexistent_citizen_returns_404(self, client, org, owner):
        headers = auth_header_for_user(owner)
        response = client.delete("/api/v1/citizens/99999", **headers)
        assert response.status_code == 404


@pytest.mark.django_db
class TestCitizenNotFound:
    def test_get_nonexistent_citizen_returns_404(self, client, org, member):
        headers = auth_header_for_user(member)
        response = client.get("/api/v1/citizens/99999", **headers)
        assert response.status_code == 404


@pytest.mark.django_db
class TestUpdateCitizenBothFields:
    def test_update_citizen_both_fields(self, client, org, member):
        from apps.citizens.models import Citizen

        citizen = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)

        headers = auth_header_for_user(member)
        response = client.patch(
            f"/api/v1/citizens/{citizen.id}",
            data={"first_name": "Bob", "last_name": "Z"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Bob"
        assert data["last_name"] == "Z"
