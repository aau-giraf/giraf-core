"""Business logic for grade operations."""

from django.db.models import QuerySet

from apps.citizens.models import Citizen
from apps.grades.models import Grade
from core.exceptions import BadRequestError, ResourceNotFoundError


class GradeService:
    @staticmethod
    def _validate_citizens_belong_to_org(citizen_ids: list[int], org_id: int) -> None:
        """Verify all citizen IDs belong to the given organization."""
        valid = set(Citizen.objects.filter(id__in=citizen_ids, organization_id=org_id).values_list("id", flat=True))
        invalid = set(citizen_ids) - valid
        if invalid:
            raise BadRequestError(f"Citizens do not belong to this organization: {sorted(invalid)}")

    @staticmethod
    def get_grade(grade_id: int) -> Grade:
        try:
            return Grade.objects.select_related("organization").get(id=grade_id)
        except Grade.DoesNotExist as e:
            raise ResourceNotFoundError(f"Grade {grade_id} not found.") from e

    @staticmethod
    def create_grade(*, name: str, org_id: int) -> Grade:
        return Grade.objects.create(name=name, organization_id=org_id)

    @staticmethod
    def list_grades(org_id: int) -> QuerySet[Grade]:
        return Grade.objects.filter(organization_id=org_id)

    @staticmethod
    def update_grade(*, grade_id: int, name: str | None = None) -> Grade:
        grade = GradeService.get_grade(grade_id)
        if name is not None:
            grade.name = name
            grade.save(update_fields=["name"])
        return grade

    @staticmethod
    def delete_grade(*, grade_id: int) -> None:
        deleted_count, _ = Grade.objects.filter(id=grade_id).delete()
        if deleted_count == 0:
            raise ResourceNotFoundError(f"Grade {grade_id} not found.")

    @staticmethod
    def assign_citizens(*, grade_id: int, citizen_ids: list[int]) -> Grade:
        grade = GradeService.get_grade(grade_id)
        GradeService._validate_citizens_belong_to_org(citizen_ids, grade.organization_id)
        grade.citizens.set(citizen_ids)
        return grade

    @staticmethod
    def add_citizens(*, grade_id: int, citizen_ids: list[int]) -> Grade:
        grade = GradeService.get_grade(grade_id)
        GradeService._validate_citizens_belong_to_org(citizen_ids, grade.organization_id)
        grade.citizens.add(*citizen_ids)
        return grade

    @staticmethod
    def remove_citizens(*, grade_id: int, citizen_ids: list[int]) -> Grade:
        grade = GradeService.get_grade(grade_id)
        GradeService._validate_citizens_belong_to_org(citizen_ids, grade.organization_id)
        grade.citizens.remove(*citizen_ids)
        return grade
