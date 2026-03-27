"""User API endpoints."""

from django.conf import settings
from ninja import File, Router
from ninja.files import UploadedFile

from apps.users.schemas import PasswordChangeIn, RegisterIn, UserOut, UserUpdateIn
from apps.users.services import UserService
from core.schemas import ErrorOut
from core.throttling import RegisterRateThrottle

router = Router(tags=["users"])


@router.post(
    "/auth/register",
    response={201: UserOut, 403: ErrorOut, 409: ErrorOut, 422: ErrorOut},
    auth=None,
    throttle=[RegisterRateThrottle()],
)
def register(request, payload: RegisterIn):
    """Register a new user account. Requires REGISTRATION_OPEN=True."""
    if not getattr(settings, "REGISTRATION_OPEN", False):
        return 403, {"detail": "Registration is currently closed."}
    user = UserService.register(
        username=payload.username,
        password=payload.password,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    return 201, user


@router.get("/users/me", response=UserOut)
def me(request):
    """Get the current authenticated user's profile."""
    return request.auth


@router.put("/users/me", response={200: UserOut, 422: ErrorOut})
def update_profile(request, payload: UserUpdateIn):
    """Update current user's profile."""
    updated = UserService.update_user(
        user_id=request.auth.id, first_name=payload.first_name, last_name=payload.last_name, email=payload.email
    )
    return 200, updated


@router.put("/users/me/password", response={200: UserOut, 422: ErrorOut})
def change_password(request, payload: PasswordChangeIn):
    """Change user's password."""
    updated = UserService.change_password(
        user_id=request.auth.id, old_password=payload.old_password, new_password=payload.new_password
    )
    return 200, updated


@router.delete("/users/me", response={204: None})
def delete_account(request):
    """Delete the current user's account."""
    UserService.delete_user(user_id=request.auth.id)
    return 204, None


@router.post("/users/me/profile-picture", response={200: UserOut, 422: ErrorOut})
def upload_profile_picture(request, file: File[UploadedFile]):
    """Upload a profile picture."""
    updated = UserService.upload_profile_picture(user_id=request.auth.id, file=file)
    return 200, updated
