"""Invitation API endpoints.

Two routers:
- org_router: org-scoped endpoints (send, list, delete) -> mounted at /organizations
- receiver_router: receiver-scoped endpoints (list received, accept, reject)
                   -> mounted at /invitations
"""

from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate
from ninja_jwt.authentication import JWTAuth

from apps.invitations.schemas import InvitationCreateIn, InvitationOut
from apps.invitations.services import InvitationService
from apps.organizations.models import OrgRole
from core.permissions import check_invitation_receiver, check_role_or_raise
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
    check_role_or_raise(request.auth, org_id, min_role=OrgRole.ADMIN)
    return 201, InvitationService.send(
        org_id=org_id,
        sender_id=request.auth.id,
        receiver_email=payload.receiver_email,
    )


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
    check_role_or_raise(request.auth, org_id, min_role=OrgRole.ADMIN)
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
    check_role_or_raise(request.auth, org_id, min_role=OrgRole.ADMIN)
    InvitationService.delete(invitation_id=invitation_id, org_id=org_id)
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
    response={200: InvitationOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def accept_invitation(request, invitation_id: int):
    inv = InvitationService.get_invitation(invitation_id)
    check_invitation_receiver(request.auth, inv)
    return InvitationService.accept(invitation_id=invitation_id)


# ---------------------------------------------------------------------------
# Receiver: POST /invitations/{invitation_id}/reject
# ---------------------------------------------------------------------------


@receiver_router.post(
    "/{invitation_id}/reject",
    response={200: InvitationOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def reject_invitation(request, invitation_id: int):
    inv = InvitationService.get_invitation(invitation_id)
    check_invitation_receiver(request.auth, inv)
    return InvitationService.reject(invitation_id=invitation_id)
