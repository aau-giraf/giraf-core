"""Pictogram API endpoints."""

from ninja import File, Form, Router
from ninja.files import UploadedFile
from ninja.pagination import LimitOffsetPagination, paginate

from apps.citizens.services import CitizenService
from apps.organizations.models import OrgRole
from apps.pictograms.schemas import PictogramCreateIn, PictogramOut, PictogramUpdateIn
from apps.pictograms.services import PictogramService
from core.permissions import check_org_or_superuser, check_role_or_raise
from core.schemas import ErrorOut

router = Router(tags=["pictograms"])


@router.post("", response={201: PictogramOut, 403: ErrorOut, 422: ErrorOut})
def create_pictogram(request, payload: PictogramCreateIn):
    """Create a pictogram. Org-scoped requires member role; global requires superuser."""
    if payload.citizen_id:
        citizen = CitizenService.get_citizen(payload.citizen_id)
        if not payload.organization_id:
            payload.organization_id = citizen.organization_id
        check_role_or_raise(request.auth, citizen.organization_id, min_role=OrgRole.MEMBER)
    else:
        check_org_or_superuser(
            request.auth, payload.organization_id, min_role=OrgRole.MEMBER, action="create global pictograms"
        )

    pictogram = PictogramService.create_pictogram(
        name=payload.name,
        image_url=payload.image_url,
        organization_id=payload.organization_id,
        citizen_id=payload.citizen_id,
        generate_image=payload.generate_image,
        generate_sound=payload.generate_sound,
    )
    return 201, pictogram


@router.get("", response=list[PictogramOut])
@paginate(LimitOffsetPagination)
def list_pictograms(
    request,
    organization_id: int | None = None,
    citizen_id: int | None = None,
    search: str | None = None,
):
    """List pictograms. Optionally filter by citizen, organization, and/or search term."""
    if citizen_id:
        citizen = CitizenService.get_citizen(citizen_id)
        check_role_or_raise(request.auth, citizen.organization_id, min_role=OrgRole.MEMBER)
        return PictogramService.list_pictograms(
            organization_id=citizen.organization_id, citizen_id=citizen_id, search=search
        )
    if organization_id:
        check_role_or_raise(request.auth, organization_id, min_role=OrgRole.MEMBER)
    return PictogramService.list_pictograms(organization_id=organization_id, search=search)


@router.post("/upload", response={201: PictogramOut, 403: ErrorOut, 422: ErrorOut})
def upload_pictogram(
    request,
    image: File[UploadedFile],
    name: Form[str],
    organization_id: Form[int | None] = None,
    citizen_id: Form[int | None] = None,
    sound: File[UploadedFile | None] = None,
    generate_sound: Form[bool] = True,
):
    """Upload a pictogram with an image file and optional sound file."""
    if citizen_id:
        citizen = CitizenService.get_citizen(citizen_id)
        if not organization_id:
            organization_id = citizen.organization_id
        check_role_or_raise(request.auth, citizen.organization_id, min_role=OrgRole.MEMBER)
    else:
        check_org_or_superuser(
            request.auth, organization_id,
            min_role=OrgRole.MEMBER, action="create global pictograms",
        )

    pictogram = PictogramService.upload_pictogram(
        name=name,
        image=image,
        organization_id=organization_id,
        citizen_id=citizen_id,
        sound=sound,
        generate_sound=generate_sound,
    )
    return 201, pictogram


@router.patch("/{pictogram_id}", response={200: PictogramOut, 403: ErrorOut, 404: ErrorOut, 422: ErrorOut})
def update_pictogram(request, pictogram_id: int, payload: PictogramUpdateIn):
    """Update a pictogram. Requires member role if org-scoped; superuser if global."""
    pictogram = PictogramService.get_pictogram(pictogram_id)
    check_org_or_superuser(
        request.auth, pictogram.organization_id, min_role=OrgRole.MEMBER, action="update global pictograms"
    )

    pictogram = PictogramService.update_pictogram(
        pictogram_id=pictogram_id,
        name=payload.name,
        image_url=payload.image_url,
        generate_image=payload.generate_image,
        regenerate_sound=payload.regenerate_sound,
    )
    return 200, pictogram


@router.post("/{pictogram_id}/sound", response={200: PictogramOut, 403: ErrorOut, 404: ErrorOut, 422: ErrorOut})
def upload_sound(request, pictogram_id: int, sound: File[UploadedFile]):
    """Upload or replace a sound file on an existing pictogram."""
    pictogram = PictogramService.get_pictogram(pictogram_id)
    check_org_or_superuser(
        request.auth, pictogram.organization_id, min_role=OrgRole.MEMBER, action="update global pictograms"
    )

    pictogram = PictogramService.update_pictogram(
        pictogram_id=pictogram_id,
        sound=sound,
    )
    return 200, pictogram


@router.get("/{pictogram_id}", response={200: PictogramOut, 404: ErrorOut})
def get_pictogram(request, pictogram_id: int):
    """Get a pictogram by ID."""
    pictogram = PictogramService.get_pictogram(pictogram_id)
    return 200, pictogram


@router.delete("/{pictogram_id}", response={204: None, 403: ErrorOut, 404: ErrorOut})
def delete_pictogram(request, pictogram_id: int):
    """Delete a pictogram. Requires member role if org-scoped; superuser if global."""
    pictogram = PictogramService.get_pictogram(pictogram_id)
    check_org_or_superuser(
        request.auth, pictogram.organization_id, min_role=OrgRole.MEMBER, action="delete global pictograms"
    )

    PictogramService.delete_pictogram(pictogram_id=pictogram_id)
    return 204, None
