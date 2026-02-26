"""Pictogram API endpoints."""

from ninja import File, Form, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja.pagination import LimitOffsetPagination, paginate

from apps.organizations.models import OrgRole
from apps.pictograms.schemas import PictogramCreateIn, PictogramOut
from apps.pictograms.services import PictogramService
from core.permissions import check_role_or_raise
from core.schemas import ErrorOut

router = Router(tags=["pictograms"])


@router.post("", response={201: PictogramOut, 403: ErrorOut, 422: ErrorOut})
def create_pictogram(request, payload: PictogramCreateIn):
    """Create a pictogram. Org-scoped requires admin role; global requires superuser."""
    if payload.organization_id:
        check_role_or_raise(request.auth, payload.organization_id, OrgRole.ADMIN)
    elif not request.auth.is_superuser:
        raise HttpError(403, "Only superusers can create global pictograms.")

    pictogram = PictogramService.create_pictogram(
        name=payload.name,
        image_url=payload.image_url,
        organization_id=payload.organization_id,
    )
    return 201, pictogram


@router.get("", response=list[PictogramOut])
@paginate(LimitOffsetPagination)
def list_pictograms(request, organization_id: int | None = None):
    """List pictograms. Returns global + org-specific if org_id provided (requires membership)."""
    if organization_id:
        check_role_or_raise(request.auth, organization_id, OrgRole.MEMBER)
    return PictogramService.list_pictograms(organization_id)


@router.post("/upload", response={201: PictogramOut, 403: ErrorOut})
def upload_pictogram(
    request,
    image: File[UploadedFile],
    name: Form[str],
    organization_id: Form[int | None] = None,
):
    """Upload a pictogram with an image file. Org-scoped requires admin; global requires superuser."""
    if organization_id:
        check_role_or_raise(request.auth, organization_id, OrgRole.ADMIN)
    elif not request.auth.is_superuser:
        raise HttpError(403, "Only superusers can create global pictograms.")

    pictogram = PictogramService.upload_pictogram(
        name=name,
        image=image,
        organization_id=organization_id,
    )
    return 201, pictogram


@router.get("/{pictogram_id}", response={200: PictogramOut, 404: ErrorOut})
def get_pictogram(request, pictogram_id: int):
    """Get a pictogram by ID."""
    pictogram = PictogramService.get_pictogram(pictogram_id)
    return 200, pictogram


@router.delete("/{pictogram_id}", response={204: None, 403: ErrorOut, 404: ErrorOut})
def delete_pictogram(request, pictogram_id: int):
    """Delete a pictogram. Requires admin role if org-scoped; superuser if global."""
    pictogram = PictogramService.get_pictogram(pictogram_id)
    if pictogram.organization_id:
        check_role_or_raise(request.auth, pictogram.organization_id, OrgRole.ADMIN)
    elif not request.auth.is_superuser:
        raise HttpError(403, "Only superusers can delete global pictograms.")

    PictogramService.delete_pictogram(pictogram_id=pictogram_id)
    return 204, None
