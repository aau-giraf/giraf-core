"""Pictogram API endpoints."""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja.pagination import LimitOffsetPagination, paginate

from apps.organizations.models import OrgRole
from apps.pictograms.models import Pictogram
from core.permissions import check_role
from core.schemas import ErrorOut

router = Router(tags=["pictograms"])


class PictogramCreateIn(Schema):
    name: str
    image_url: str
    organization_id: int | None = None


class PictogramOut(Schema):
    id: int
    name: str
    image_url: str
    organization_id: int | None

    @staticmethod
    def resolve_image_url(obj):
        """Return image file URL if uploaded, otherwise the stored image_url."""
        if obj.image:
            return obj.image.url
        return obj.image_url


@router.post("", response={201: PictogramOut, 403: ErrorOut})
def create_pictogram(request, payload: PictogramCreateIn):
    """Create a pictogram. If org-scoped, requires admin role in that org."""
    if payload.organization_id:
        allowed, msg = check_role(request.auth, payload.organization_id, min_role=OrgRole.ADMIN)
        if not allowed:
            raise HttpError(403, msg)
    pictogram = Pictogram.objects.create(
        name=payload.name,
        image_url=payload.image_url,
        organization_id=payload.organization_id,
    )
    return 201, pictogram


@router.get("", response=list[PictogramOut])
@paginate(LimitOffsetPagination)
def list_pictograms(request, organization_id: int | None = None):
    """List pictograms. Returns global + org-specific if org_id provided."""
    if organization_id:
        return Pictogram.objects.filter(
            Q(organization_id=organization_id) | Q(organization__isnull=True)
        )
    return Pictogram.objects.filter(organization__isnull=True)


@router.get("/{pictogram_id}", response={200: PictogramOut, 404: ErrorOut})
def get_pictogram(request, pictogram_id: int):
    """Get a pictogram by ID."""
    return 200, get_object_or_404(Pictogram, id=pictogram_id)


@router.delete("/{pictogram_id}", response={204: None, 403: ErrorOut, 404: ErrorOut})
def delete_pictogram(request, pictogram_id: int):
    """Delete a pictogram. Requires admin role if org-scoped."""
    pictogram = get_object_or_404(Pictogram, id=pictogram_id)
    if pictogram.organization_id:
        allowed, msg = check_role(request.auth, pictogram.organization_id, min_role=OrgRole.ADMIN)
        if not allowed:
            raise HttpError(403, msg)
    pictogram.delete()
    return 204, None


@router.post("/upload", response={201: PictogramOut, 403: ErrorOut})
def upload_pictogram(
    request,
    image: File[UploadedFile],
    name: Form[str],
    organization_id: Form[int | None] = None,
):
    """Upload a pictogram with an image file. Requires admin role if org-scoped."""
    if organization_id:
        allowed, msg = check_role(request.auth, organization_id, min_role=OrgRole.ADMIN)
        if not allowed:
            raise HttpError(403, msg)
    pictogram = Pictogram.objects.create(
        name=name,
        image=image,
        organization_id=organization_id,
    )
    return 201, pictogram
