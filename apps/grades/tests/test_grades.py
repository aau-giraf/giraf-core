"""Tests for Grade model and API endpoints.

Grades are class groupings of citizens within an organization.
"""
import pytest

from apps.citizens.models import Citizen
from apps.grades.models import Grade
from apps.organizations.models import Membership, Organization, OrgRole
from apps.users.tests.factories import UserFactory
from conftest import auth_header


@pytest.mark.django_db
class TestGradeModel:
    def test_create_grade(self):
        org = Organization.objects.create(name="Test School")
        grade = Grade.objects.create(name="Class 3A", organization=org)
        assert grade.pk is not None
        assert str(grade) == "Class 3A"

    def test_grade_citizens_m2m(self):
        org = Organization.objects.create(name="Test School")
        grade = Grade.objects.create(name="Class 3A", organization=org)
        c1 = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)
        c2 = Citizen.objects.create(first_name="Bob", last_name="B", organization=org)
        grade.citizens.add(c1, c2)
        assert grade.citizens.count() == 2

    def test_cascade_delete_org_deletes_grades(self):
        org = Organization.objects.create(name="Test School")
        Grade.objects.create(name="Class 3A", organization=org)
        org.delete()
        assert Grade.objects.count() == 0


@pytest.mark.django_db
class TestGradeAPI:
    def test_create_grade(self, client, org, owner):
        headers = auth_header(client, "owner")
        response = client.post(
            f"/api/v1/organizations/{org.id}/grades",
            data={"name": "Class 3A"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Class 3A"

    def test_non_member_cannot_create_grade(self, client, org, non_member):
        headers = auth_header(client, "outsider")
        response = client.post(
            f"/api/v1/organizations/{org.id}/grades",
            data={"name": "Class 3A"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403

    def test_list_grades(self, client, org, member):
        Grade.objects.create(name="Class 3A", organization=org)
        Grade.objects.create(name="Class 3B", organization=org)

        headers = auth_header(client, "member")
        response = client.get(f"/api/v1/organizations/{org.id}/grades", **headers)
        assert response.status_code == 200
        assert len(response.json()["items"]) == 2

    def test_list_grades_pagination(self, client, org, member):
        """Verify pagination params work on list endpoint."""
        for i in range(5):
            Grade.objects.create(name=f"Class {i}", organization=org)
        headers = auth_header(client, "member")
        response = client.get(
            f"/api/v1/organizations/{org.id}/grades?limit=2&offset=0", **headers
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 2
        assert body["count"] == 5

    def test_update_grade(self, client, org, owner):
        grade = Grade.objects.create(name="Class 3A", organization=org)
        headers = auth_header(client, "owner")
        response = client.patch(
            f"/api/v1/grades/{grade.id}",
            data={"name": "Class 4A"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Class 4A"

    def test_delete_grade(self, client, org, owner):
        grade = Grade.objects.create(name="Class 3A", organization=org)
        headers = auth_header(client, "owner")
        response = client.delete(f"/api/v1/grades/{grade.id}", **headers)
        assert response.status_code == 204

    def test_assign_citizens_to_grade(self, client, org, owner):
        grade = Grade.objects.create(name="Class 3A", organization=org)
        c1 = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)
        c2 = Citizen.objects.create(first_name="Bob", last_name="B", organization=org)

        headers = auth_header(client, "owner")
        response = client.post(
            f"/api/v1/grades/{grade.id}/citizens",
            data={"citizen_ids": [c1.id, c2.id]},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        grade.refresh_from_db()
        assert grade.citizens.count() == 2

    def test_member_cannot_delete_grade(self, client, org, member):
        grade = Grade.objects.create(name="Class 3A", organization=org)
        headers = auth_header(client, "member")
        response = client.delete(f"/api/v1/grades/{grade.id}", **headers)
        assert response.status_code == 403


@pytest.mark.django_db
class TestCrossOrgCitizenAssignment:
    """Tests for the cross-org citizen assignment vulnerability fix."""

    def test_assign_citizens_from_other_org_rejected(self, client, org, owner):
        """Cannot assign citizens from a different organization to a grade."""
        other_org = Organization.objects.create(name="Other School")
        grade = Grade.objects.create(name="Class 3A", organization=org)
        foreign_citizen = Citizen.objects.create(
            first_name="Eve", last_name="F", organization=other_org
        )

        headers = auth_header(client, "owner")
        response = client.post(
            f"/api/v1/grades/{grade.id}/citizens",
            data={"citizen_ids": [foreign_citizen.id]},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 400
        assert grade.citizens.count() == 0

    def test_add_citizens_from_other_org_rejected(self, client, org, owner):
        """Cannot add citizens from a different org via the add endpoint."""
        other_org = Organization.objects.create(name="Other School")
        grade = Grade.objects.create(name="Class 3A", organization=org)
        foreign_citizen = Citizen.objects.create(
            first_name="Eve", last_name="F", organization=other_org
        )

        headers = auth_header(client, "owner")
        response = client.post(
            f"/api/v1/grades/{grade.id}/citizens/add",
            data={"citizen_ids": [foreign_citizen.id]},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 400
        assert grade.citizens.count() == 0

    def test_mix_valid_and_invalid_citizens_rejected(self, client, org, owner):
        """If any citizen is from another org, the entire request is rejected."""
        other_org = Organization.objects.create(name="Other School")
        grade = Grade.objects.create(name="Class 3A", organization=org)
        valid_citizen = Citizen.objects.create(
            first_name="Alice", last_name="A", organization=org
        )
        foreign_citizen = Citizen.objects.create(
            first_name="Eve", last_name="F", organization=other_org
        )

        headers = auth_header(client, "owner")
        response = client.post(
            f"/api/v1/grades/{grade.id}/citizens",
            data={"citizen_ids": [valid_citizen.id, foreign_citizen.id]},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 400
        assert grade.citizens.count() == 0

    def test_nonexistent_citizen_ids_rejected(self, client, org, owner):
        """Non-existent citizen IDs are also rejected."""
        grade = Grade.objects.create(name="Class 3A", organization=org)

        headers = auth_header(client, "owner")
        response = client.post(
            f"/api/v1/grades/{grade.id}/citizens",
            data={"citizen_ids": [99999]},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 400

    def test_valid_same_org_citizens_accepted(self, client, org, owner):
        """Citizens from the same org should be accepted normally."""
        grade = Grade.objects.create(name="Class 3A", organization=org)
        c1 = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)
        c2 = Citizen.objects.create(first_name="Bob", last_name="B", organization=org)

        headers = auth_header(client, "owner")
        response = client.post(
            f"/api/v1/grades/{grade.id}/citizens",
            data={"citizen_ids": [c1.id, c2.id]},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        assert grade.citizens.count() == 2
