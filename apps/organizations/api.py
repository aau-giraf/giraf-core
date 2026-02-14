"""Organization API endpoints."""
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from apps.organizations.models import Organization
from apps.organizations.schemas import MemberOut, MemberRoleUpdateIn, OrgCreateIn, OrgOut, OrgUpdateIn
from apps.organizations.services import OrganizationService
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
    org = get_object_or_404(Organization, id=org_id)
    membership = OrganizationService.get_membership(request.auth, org_id)
    if not membership:
        raise HttpError(403, "You are not a member of this organization.")
    return 200, org


@router.patch(
    "/{org_id}",
    response={200: OrgOut, 403: ErrorOut, 404: ErrorOut},
)
def update_organization(request, org_id: int, payload: OrgUpdateIn):
    """Update an organization. Only owners can do this."""
    org = get_object_or_404(Organization, id=org_id)
    membership = OrganizationService.get_membership(request.auth, org_id)
    if not membership or not membership.is_owner:
        raise HttpError(403, "Only organization owners can update the organization.")
    org.name = payload.name
    org.save()
    return 200, org


@router.delete(
    "/{org_id}",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
)
def delete_organization(request, org_id: int):
    """Delete an organization. Only owners can do this."""
    org = get_object_or_404(Organization, id=org_id)
    membership = OrganizationService.get_membership(request.auth, org_id)
    if not membership or not membership.is_owner:
        raise HttpError(403, "Only organization owners can delete the organization.")
    org.delete()
    return 204, None


@router.get("/{org_id}/members", response=list[MemberOut])
@paginate(LimitOffsetPagination)
def list_members(request, org_id: int):
    """List members of an organization. Must be a member."""
    membership = OrganizationService.get_membership(request.auth, org_id)
    if not membership:
        raise HttpError(403, "You are not a member of this organization.")
    return OrganizationService.get_org_members(org_id)


@router.patch(
    "/{org_id}/members/{user_id}",
    response={200: MemberOut, 403: ErrorOut, 404: ErrorOut},
)
def update_member_role(request, org_id: int, user_id: int, payload: MemberRoleUpdateIn):
    """Update a member's role. Only owners can do this."""
    membership = OrganizationService.get_membership(request.auth, org_id)
    if not membership or not membership.is_owner:
        raise HttpError(403, "Only organization owners can change member roles.")
    updated = OrganizationService.update_member_role(org_id, user_id, payload.role)
    return 200, updated


@router.delete(
    "/{org_id}/members/{user_id}",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
)
def remove_member(request, org_id: int, user_id: int):
    """Remove a member from an organization. Admins and owners can do this."""
    membership = OrganizationService.get_membership(request.auth, org_id)
    if not membership or not membership.is_admin:
        raise HttpError(403, "Only admins and owners can remove members.")
    OrganizationService.remove_member(org_id, user_id)
    return 204, None
