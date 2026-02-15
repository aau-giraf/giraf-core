"""Invitation API endpoints.

Two routers:
- org_router: org-scoped endpoints (send, list, delete) -> mounted at /organizations
- receiver_router: receiver-scoped endpoints (list received, accept, reject)
                   -> mounted at /invitations
"""

from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate
from ninja_jwt.authentication import JWTAuth

from apps.invitations.models import Invitation
from apps.invitations.schemas import InvitationCreateIn, InvitationOut
from apps.invitations.services import InvitationService
from apps.organizations.models import Organization
from core.exceptions import AlreadyMemberError, DuplicateInvitationError, ReceiverNotFoundError
from core.permissions import check_role
from core.schemas import ErrorOut
from core.throttling import InvitationSendRateThrottle

org_router = Router(tags=["Invitations"])
receiver_router = Router(tags=["Invitations"])


# ---------------------------------------------------------------------------
# Org-scoped: POST /organizations/{org_id}/invitations
# ---------------------------------------------------------------------------


@org_router.post(
    "/{org_id}/invitations",
    response={201: InvitationOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 409: ErrorOut},
    auth=JWTAuth(),
    throttle=[InvitationSendRateThrottle()],
)
def send_invitation(request, org_id: int, payload: InvitationCreateIn):
    ok, msg = check_role(request.auth, org_id, min_role="admin")
    if not ok:
        raise HttpError(403, msg)

    org = get_object_or_404(Organization, id=org_id)
    try:
        result = InvitationService.send(
            organization=org,
            sender=request.auth,
            receiver_email=payload.receiver_email,
        )
    except (ReceiverNotFoundError, AlreadyMemberError):
        raise HttpError(400, "Cannot send invitation.")
    except DuplicateInvitationError:
        raise HttpError(409, "Pending invitation already exists.")

    inv = Invitation.objects.select_related("organization", "sender", "receiver").get(id=result.id)
    return 201, inv


# ---------------------------------------------------------------------------
# Org-scoped: GET /organizations/{org_id}/invitations
# ---------------------------------------------------------------------------


@org_router.get(
    "/{org_id}/invitations",
    response=list[InvitationOut],
    auth=JWTAuth(),
)
@paginate(LimitOffsetPagination)
def list_org_invitations(request, org_id: int):
    ok, msg = check_role(request.auth, org_id, min_role="admin")
    if not ok:
        raise HttpError(403, msg)
    return InvitationService.list_for_org(org_id)


# ---------------------------------------------------------------------------
# Org-scoped: DELETE /organizations/{org_id}/invitations/{invitation_id}
# ---------------------------------------------------------------------------


@org_router.delete(
    "/{org_id}/invitations/{invitation_id}",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_invitation(request, org_id: int, invitation_id: int):
    ok, msg = check_role(request.auth, org_id, min_role="admin")
    if not ok:
        raise HttpError(403, msg)
    inv = get_object_or_404(Invitation, id=invitation_id, organization_id=org_id)
    InvitationService.delete(inv)
    return 204, None


# ---------------------------------------------------------------------------
# Receiver: GET /invitations/received
# ---------------------------------------------------------------------------


@receiver_router.get(
    "/received",
    response=list[InvitationOut],
    auth=JWTAuth(),
)
@paginate(LimitOffsetPagination)
def list_received_invitations(request):
    return InvitationService.list_received(request.auth)


# ---------------------------------------------------------------------------
# Receiver: POST /invitations/{invitation_id}/accept
# ---------------------------------------------------------------------------


@receiver_router.post(
    "/{invitation_id}/accept",
    response={200: InvitationOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def accept_invitation(request, invitation_id: int):
    inv = get_object_or_404(
        Invitation.objects.select_related("organization", "sender", "receiver"),
        id=invitation_id,
    )
    if inv.receiver_id != request.auth.id:
        raise HttpError(403, "Only the receiver can respond.")
    InvitationService.accept(inv)
    inv.refresh_from_db()
    return inv


# ---------------------------------------------------------------------------
# Receiver: POST /invitations/{invitation_id}/reject
# ---------------------------------------------------------------------------


@receiver_router.post(
    "/{invitation_id}/reject",
    response={200: InvitationOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def reject_invitation(request, invitation_id: int):
    inv = get_object_or_404(
        Invitation.objects.select_related("organization", "sender", "receiver"),
        id=invitation_id,
    )
    if inv.receiver_id != request.auth.id:
        raise HttpError(403, "Only the receiver can respond.")
    InvitationService.reject(inv)
    inv.refresh_from_db()
    return inv
