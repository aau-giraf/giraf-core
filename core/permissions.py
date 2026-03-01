"""Cross-cutting permission utilities for GIRAF Core API.

Reusable helpers for checking organization membership and role-based access.
All role checks use the hierarchy: OWNER > ADMIN > MEMBER.
"""

from ninja.errors import HttpError

from apps.organizations.models import ROLE_HIERARCHY, Membership


def get_membership_or_none(user, org_id: int) -> Membership | None:
    """Get the user's membership for an organization, or None if not a member."""
    try:
        return Membership.objects.select_related("organization").get(user=user, organization_id=org_id)
    except Membership.DoesNotExist:
        return None


def check_role(user, org_id: int, *, min_role: str) -> tuple[bool, str]:
    """Check if a user has at least the given role in an organization.

    Returns:
        (True, "") if the user has sufficient permissions.
        (False, reason) if the user lacks permissions.
    """
    membership = get_membership_or_none(user, org_id)
    if membership is None:
        return False, "You are not a member of this organization."

    user_level = ROLE_HIERARCHY.get(membership.role, -1)
    required_level = ROLE_HIERARCHY.get(min_role, 999)

    if user_level >= required_level:
        return True, ""

    return False, f"Insufficient permissions. Required: {min_role}, your role: {membership.role}."


def check_role_or_raise(user, org_id: int, min_role: str) -> None:
    """Check role and raise HttpError(403) if insufficient."""
    allowed, msg = check_role(user, org_id, min_role=min_role)
    if not allowed:
        raise HttpError(403, msg)


def check_org_or_superuser(user, org_id: int | None, *, min_role: str, action: str) -> None:
    """Require org role if org-scoped, or superuser if global.

    Raises HttpError(403) if the user lacks permission.
    """
    if org_id:
        check_role_or_raise(user, org_id, min_role)
    elif not user.is_superuser:
        raise HttpError(403, f"Only superusers can {action}.")
