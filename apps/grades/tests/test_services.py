"""Tests for GradeService."""

import pytest

from apps.citizens.models import Citizen
from apps.grades.models import Grade
from apps.grades.services import GradeService
from apps.organizations.models import Organization
from core.exceptions import BadRequestError, ResourceNotFoundError


@pytest.mark.django_db
class TestGradeService:
    @pytest.fixture
    def org(self):
        return Organization.objects.create(name="Test School")

    @pytest.fixture
    def other_org(self):
        return Organization.objects.create(name="Other School")

    @pytest.fixture
    def grade(self, org):
        return GradeService.create_grade(name="Class 3A", org_id=org.id)

    def test_get_nonexistent_raises(self):
        with pytest.raises(ResourceNotFoundError, match="Grade 99999 not found"):
            GradeService.get_grade(99999)

    def test_create_grade(self, org):
        grade = GradeService.create_grade(name="Class 3A", org_id=org.id)
        assert grade.pk is not None
        assert grade.name == "Class 3A"
        assert grade.organization_id == org.id

    def test_list_grades(self, org, other_org):
        GradeService.create_grade(name="Class 3A", org_id=org.id)
        GradeService.create_grade(name="Class 3B", org_id=org.id)
        GradeService.create_grade(name="Other", org_id=other_org.id)
        assert GradeService.list_grades(org.id).count() == 2

    def test_update_grade(self, grade):
        updated = GradeService.update_grade(grade_id=grade.id, name="Class 4A")
        assert updated.name == "Class 4A"

    def test_delete_grade(self, grade):
        grade_id = grade.id
        GradeService.delete_grade(grade_id=grade_id)
        assert not Grade.objects.filter(id=grade_id).exists()

    def test_assign_citizens_cross_org_raises(self, org, other_org, grade):
        foreign = Citizen.objects.create(first_name="Eve", last_name="F", organization=other_org)
        with pytest.raises(BadRequestError, match="do not belong"):
            GradeService.assign_citizens(grade_id=grade.id, citizen_ids=[foreign.id])

    def test_add_citizens_cross_org_raises(self, org, other_org, grade):
        foreign = Citizen.objects.create(first_name="Eve", last_name="F", organization=other_org)
        with pytest.raises(BadRequestError, match="do not belong"):
            GradeService.add_citizens(grade_id=grade.id, citizen_ids=[foreign.id])

    def test_remove_citizens_cross_org_raises(self, org, other_org, grade):
        foreign = Citizen.objects.create(first_name="Eve", last_name="F", organization=other_org)
        with pytest.raises(BadRequestError, match="do not belong"):
            GradeService.remove_citizens(grade_id=grade.id, citizen_ids=[foreign.id])

    def test_assign_nonexistent_citizen_raises(self, grade):
        with pytest.raises(BadRequestError, match="do not belong"):
            GradeService.assign_citizens(grade_id=grade.id, citizen_ids=[99999])

    def test_assign_mix_valid_and_invalid_raises(self, org, other_org, grade):
        valid = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)
        foreign = Citizen.objects.create(first_name="Eve", last_name="F", organization=other_org)
        with pytest.raises(BadRequestError):
            GradeService.assign_citizens(grade_id=grade.id, citizen_ids=[valid.id, foreign.id])
        assert grade.citizens.count() == 0

    def test_assign_citizens_success(self, org, grade):
        c1 = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)
        c2 = Citizen.objects.create(first_name="Bob", last_name="B", organization=org)
        result = GradeService.assign_citizens(grade_id=grade.id, citizen_ids=[c1.id, c2.id])
        assert result.citizens.count() == 2

    def test_add_citizens_success(self, org, grade):
        c1 = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)
        GradeService.add_citizens(grade_id=grade.id, citizen_ids=[c1.id])
        assert grade.citizens.count() == 1

    def test_remove_citizens_success(self, org, grade):
        c1 = Citizen.objects.create(first_name="Alice", last_name="A", organization=org)
        grade.citizens.add(c1)
        GradeService.remove_citizens(grade_id=grade.id, citizen_ids=[c1.id])
        assert grade.citizens.count() == 0
