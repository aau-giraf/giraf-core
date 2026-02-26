"""Organization API endpoints."""

from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

from apps.organizations.models import OrgRole
from apps.organizations.schemas import MemberOut, MemberRoleUpdateIn, OrgCreateIn, OrgOut, OrgUpdateIn
from apps.organizations.services import OrganizationService
from core.permissions import check_role_or_raise
from core.schemas import ErrorOut

router = Router(tags=["organizations"])


@router.post("", response={201: OrgOut})
def create_organization(request, payload: OrgCreateIn):
    """Create an organization. The creator becomes the owner."""
    org = OrganizationService.create_organization(name=payload.name, creator=request.auth)
    return 201, org


@router.get("", response=list[OrgOut])
@paginate(LimitOffsetPagination)
def list_organizations(request):
    """List organizations the current user belongs to."""
    return OrganizationService.get_user_organizations(request.auth)


@router.get("/{org_id}", response={200: OrgOut, 403: ErrorOut, 404: ErrorOut})
def get_organization(request, org_id: int):
    """Get organization detail. Must be a member."""
    check_role_or_raise(request.auth, org_id, OrgRole.MEMBER)
    org = OrganizationService.get_organization(org_id)
    return 200, org


@router.patch(
    "/{org_id}",
    response={200: OrgOut, 403: ErrorOut, 404: ErrorOut},
)
def update_organization(request, org_id: int, payload: OrgUpdateIn):
    """Update an organization. Only owners can do this."""
    check_role_or_raise(request.auth, org_id, OrgRole.OWNER)
    org = OrganizationService.update_organization(org_id=org_id, name=payload.name)
    return 200, org


@router.delete(
    "/{org_id}",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
)
def delete_organization(request, org_id: int):
    """Delete an organization. Only owners can do this."""
    check_role_or_raise(request.auth, org_id, OrgRole.OWNER)
    OrganizationService.delete_organization(org_id=org_id)
    return 204, None


@router.get("/{org_id}/members", response=list[MemberOut])
@paginate(LimitOffsetPagination)
def list_members(request, org_id: int):
    """List members of an organization. Must be a member."""
    check_role_or_raise(request.auth, org_id, OrgRole.MEMBER)
    return OrganizationService.get_org_members(org_id)


@router.patch(
    "/{org_id}/members/{user_id}",
    response={200: MemberOut, 403: ErrorOut, 404: ErrorOut},
)
def update_member_role(request, org_id: int, user_id: int, payload: MemberRoleUpdateIn):
    """Update a member's role. Only owners can do this."""
    check_role_or_raise(request.auth, org_id, OrgRole.OWNER)
    updated = OrganizationService.update_member_role(org_id, user_id, payload.role, requesting_user=request.auth)
    return 200, updated


@router.delete(
    "/{org_id}/members/{user_id}",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
)
def remove_member(request, org_id: int, user_id: int):
    """Remove a member from an organization. Admins and owners can do this."""
    check_role_or_raise(request.auth, org_id, OrgRole.ADMIN)
    OrganizationService.remove_member(org_id, user_id, requesting_user=request.auth)
    return 204, None
