"""Tests for Citizen model."""

import pytest

from apps.organizations.models import Organization


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
