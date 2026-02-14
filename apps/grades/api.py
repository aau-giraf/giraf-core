"""Grade API endpoints."""
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from apps.grades.models import Grade
from apps.grades.schemas import GradeCitizenAssignIn, GradeCreateIn, GradeOut, GradeUpdateIn
from apps.organizations.models import OrgRole
from core.permissions import check_role

router = Router(tags=["grades"])


class ErrorOut(Schema):
    detail: str


@router.post(
    "/organizations/{org_id}/grades",
    response={201: GradeOut, 403: ErrorOut},
)
def create_grade(request, org_id: int, payload: GradeCreateIn):
    """Create a grade in an organization. Requires admin role."""
    allowed, msg = check_role(request.auth, org_id, min_role=OrgRole.ADMIN)
    if not allowed:
        return 403, {"detail": msg}
    grade = Grade.objects.create(name=payload.name, organization_id=org_id)
    return 201, grade


@router.get(
    "/organizations/{org_id}/grades",
    response=list[GradeOut],
)
@paginate(LimitOffsetPagination)
def list_grades(request, org_id: int):
    """List grades in an organization. Requires membership."""
    allowed, msg = check_role(request.auth, org_id, min_role=OrgRole.MEMBER)
    if not allowed:
        raise HttpError(403, msg)
    return Grade.objects.filter(organization_id=org_id)


@router.patch(
    "/grades/{grade_id}",
    response={200: GradeOut, 403: ErrorOut, 404: ErrorOut},
)
def update_grade(request, grade_id: int, payload: GradeUpdateIn):
    """Update a grade. Requires admin role in the grade's org."""
    grade = get_object_or_404(Grade, id=grade_id)
    allowed, msg = check_role(request.auth, grade.organization_id, min_role=OrgRole.ADMIN)
    if not allowed:
        return 403, {"detail": msg}
    if payload.name is not None:
        grade.name = payload.name
    grade.save()
    return 200, grade


@router.delete(
    "/grades/{grade_id}",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
)
def delete_grade(request, grade_id: int):
    """Delete a grade. Requires admin role in the grade's org."""
    grade = get_object_or_404(Grade, id=grade_id)
    allowed, msg = check_role(request.auth, grade.organization_id, min_role=OrgRole.ADMIN)
    if not allowed:
        return 403, {"detail": msg}
    grade.delete()
    return 204, None


@router.get(
    "/grades/{grade_id}",
    response={200: GradeOut, 403: ErrorOut, 404: ErrorOut},
)
def get_grade(request, grade_id: int):
    """Get a grade by ID. Requires membership in the grade's org."""
    grade = get_object_or_404(Grade, id=grade_id)
    allowed, msg = check_role(request.auth, grade.organization_id, min_role=OrgRole.MEMBER)
    if not allowed:
        return 403, {"detail": msg}
    return 200, grade


@router.post(
    "/grades/{grade_id}/citizens",
    response={200: GradeOut, 403: ErrorOut, 404: ErrorOut},
)
def assign_citizens(request, grade_id: int, payload: GradeCitizenAssignIn):
    """Assign citizens to a grade (replaces entire set). Requires admin role."""
    grade = get_object_or_404(Grade, id=grade_id)
    allowed, msg = check_role(request.auth, grade.organization_id, min_role=OrgRole.ADMIN)
    if not allowed:
        return 403, {"detail": msg}
    grade.citizens.set(payload.citizen_ids)
    return 200, grade


@router.post(
    "/grades/{grade_id}/citizens/add",
    response={200: GradeOut, 403: ErrorOut, 404: ErrorOut},
)
def add_citizens_to_grade(request, grade_id: int, payload: GradeCitizenAssignIn):
    """Add citizens to a grade without removing existing ones. Requires admin role."""
    grade = get_object_or_404(Grade, id=grade_id)
    allowed, msg = check_role(request.auth, grade.organization_id, min_role=OrgRole.ADMIN)
    if not allowed:
        return 403, {"detail": msg}
    grade.citizens.add(*payload.citizen_ids)
    return 200, grade


@router.post(
    "/grades/{grade_id}/citizens/remove",
    response={200: GradeOut, 403: ErrorOut, 404: ErrorOut},
)
def remove_citizens_from_grade(request, grade_id: int, payload: GradeCitizenAssignIn):
    """Remove citizens from a grade. Requires admin role."""
    grade = get_object_or_404(Grade, id=grade_id)
    allowed, msg = check_role(request.auth, grade.organization_id, min_role=OrgRole.ADMIN)
    if not allowed:
        return 403, {"detail": msg}
    grade.citizens.remove(*payload.citizen_ids)
    return 200, grade
