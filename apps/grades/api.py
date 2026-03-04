"""Grade API endpoints."""

from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from apps.grades.schemas import GradeCitizenAssignIn, GradeCreateIn, GradeOut, GradeUpdateIn
from apps.grades.services import GradeService
from apps.organizations.models import OrgRole
from core.permissions import check_role_or_raise
from core.schemas import ErrorOut

router = Router(tags=["grades"])


@router.post(
    "/organizations/{org_id}/grades",
    response={201: GradeOut, 403: ErrorOut},
)
def create_grade(request, org_id: int, payload: GradeCreateIn):
    """Create a grade in an organization. Requires admin role."""
    check_role_or_raise(request.auth, org_id, min_role=OrgRole.ADMIN)
    grade = GradeService.create_grade(name=payload.name, org_id=org_id)
    return 201, grade


@router.get(
    "/organizations/{org_id}/grades",
    response=list[GradeOut],
)
@paginate(LimitOffsetPagination)
def list_grades(request, org_id: int):
    """List grades in an organization. Requires membership."""
    check_role_or_raise(request.auth, org_id, min_role=OrgRole.MEMBER)
    return GradeService.list_grades(org_id)


@router.patch(
    "/grades/{grade_id}",
    response={200: GradeOut, 403: ErrorOut, 404: ErrorOut},
)
def update_grade(request, grade_id: int, payload: GradeUpdateIn):
    """Update a grade. Requires admin role in the grade's org."""
    grade = GradeService.get_grade(grade_id)
    check_role_or_raise(request.auth, grade.organization_id, min_role=OrgRole.ADMIN)
    updated = GradeService.update_grade(grade_id=grade_id, name=payload.name)
    return 200, updated


@router.delete(
    "/grades/{grade_id}",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
)
def delete_grade(request, grade_id: int):
    """Delete a grade. Requires admin role in the grade's org."""
    grade = GradeService.get_grade(grade_id)
    check_role_or_raise(request.auth, grade.organization_id, min_role=OrgRole.ADMIN)
    GradeService.delete_grade(grade_id=grade_id)
    return 204, None


@router.get(
    "/grades/{grade_id}",
    response={200: GradeOut, 403: ErrorOut, 404: ErrorOut},
)
def get_grade(request, grade_id: int):
    """Get a grade by ID. Requires membership in the grade's org."""
    grade = GradeService.get_grade(grade_id)
    check_role_or_raise(request.auth, grade.organization_id, min_role=OrgRole.MEMBER)
    return 200, grade


@router.post(
    "/grades/{grade_id}/citizens",
    response={200: GradeOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
)
def assign_citizens(request, grade_id: int, payload: GradeCitizenAssignIn):
    """Assign citizens to a grade (replaces entire set). Requires admin role."""
    grade = GradeService.get_grade(grade_id)
    check_role_or_raise(request.auth, grade.organization_id, min_role=OrgRole.ADMIN)
    updated = GradeService.assign_citizens(grade_id=grade_id, citizen_ids=payload.citizen_ids)
    return 200, updated


@router.post(
    "/grades/{grade_id}/citizens/add",
    response={200: GradeOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
)
def add_citizens_to_grade(request, grade_id: int, payload: GradeCitizenAssignIn):
    """Add citizens to a grade without removing existing ones. Requires admin role."""
    grade = GradeService.get_grade(grade_id)
    check_role_or_raise(request.auth, grade.organization_id, min_role=OrgRole.ADMIN)
    updated = GradeService.add_citizens(grade_id=grade_id, citizen_ids=payload.citizen_ids)
    return 200, updated


@router.post(
    "/grades/{grade_id}/citizens/remove",
    response={200: GradeOut, 403: ErrorOut, 404: ErrorOut},
)
def remove_citizens_from_grade(request, grade_id: int, payload: GradeCitizenAssignIn):
    """Remove citizens from a grade. Requires admin role."""
    grade = GradeService.get_grade(grade_id)
    check_role_or_raise(request.auth, grade.organization_id, min_role=OrgRole.ADMIN)
    updated = GradeService.remove_citizens(grade_id=grade_id, citizen_ids=payload.citizen_ids)
    return 200, updated
