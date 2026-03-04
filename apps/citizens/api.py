"""Citizen API endpoints."""

from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from apps.citizens.schemas import CitizenCreateIn, CitizenOut, CitizenUpdateIn
from apps.citizens.services import CitizenService
from apps.organizations.models import OrgRole
from core.permissions import check_role_or_raise
from core.schemas import ErrorOut

router = Router(tags=["citizens"])


# --- Org-scoped endpoints ---


@router.post(
    "/organizations/{org_id}/citizens",
    response={201: CitizenOut, 403: ErrorOut},
)
def create_citizen(request, org_id: int, payload: CitizenCreateIn):
    """Create a citizen in an organization. Requires membership."""
    check_role_or_raise(request.auth, org_id, min_role=OrgRole.MEMBER)
    citizen = CitizenService.create_citizen(org_id=org_id, first_name=payload.first_name, last_name=payload.last_name)
    return 201, citizen


@router.get(
    "/organizations/{org_id}/citizens",
    response=list[CitizenOut],
)
@paginate(LimitOffsetPagination)
def list_citizens(request, org_id: int):
    """List citizens in an organization. Requires membership."""
    check_role_or_raise(request.auth, org_id, min_role=OrgRole.MEMBER)
    return CitizenService.list_citizens(org_id)


# --- Citizen-scoped endpoints ---


@router.get(
    "/citizens/{citizen_id}",
    response={200: CitizenOut, 403: ErrorOut, 404: ErrorOut},
)
def get_citizen(request, citizen_id: int):
    """Get citizen detail. Requires membership in the citizen's org."""
    citizen = CitizenService.get_citizen(citizen_id)
    check_role_or_raise(request.auth, citizen.organization_id, min_role=OrgRole.MEMBER)
    return 200, citizen


@router.patch(
    "/citizens/{citizen_id}",
    response={200: CitizenOut, 403: ErrorOut, 404: ErrorOut},
)
def update_citizen(request, citizen_id: int, payload: CitizenUpdateIn):
    """Update a citizen. Requires membership in the citizen's org."""
    citizen = CitizenService.get_citizen(citizen_id)
    check_role_or_raise(request.auth, citizen.organization_id, min_role=OrgRole.MEMBER)
    updated = CitizenService.update_citizen(
        citizen_id=citizen_id, first_name=payload.first_name, last_name=payload.last_name
    )
    return 200, updated


@router.delete(
    "/citizens/{citizen_id}",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
)
def delete_citizen(request, citizen_id: int):
    """Delete a citizen. Requires admin role in the citizen's org."""
    citizen = CitizenService.get_citizen(citizen_id)
    check_role_or_raise(request.auth, citizen.organization_id, min_role=OrgRole.ADMIN)
    CitizenService.delete_citizen(citizen_id=citizen_id)
    return 204, None
