"""Tests for Grade model."""

import pytest

from apps.citizens.models import Citizen
from apps.grades.models import Grade
from apps.organizations.models import Organization


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
