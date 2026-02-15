"""Business logic for organization operations."""

from django.shortcuts import get_object_or_404

from apps.organizations.models import Membership, Organization, OrgRole
from apps.users.models import User


class OrganizationService:
    @staticmethod
    def create_organization(*, name: str, creator: User) -> Organization:
        """Create an organization and make the creator the owner."""
        org = Organization.objects.create(name=name)
        Membership.objects.create(user=creator, organization=org, role=OrgRole.OWNER)
        return org

    @staticmethod
    def get_user_organizations(user: User):
        """Return organizations the user is a member of."""
        org_ids = Membership.objects.filter(user=user).values_list("organization_id", flat=True)
        return Organization.objects.filter(id__in=org_ids)

    @staticmethod
    def get_membership(user: User, org_id: int) -> Membership | None:
        """Get the user's membership for an organization, or None."""
        try:
            return Membership.objects.select_related("organization").get(user=user, organization_id=org_id)
        except Membership.DoesNotExist:
            return None

    @staticmethod
    def get_org_members(org_id: int):
        """Return all memberships for an organization."""
        return Membership.objects.filter(organization_id=org_id).select_related("user")

    @staticmethod
    def update_member_role(org_id: int, target_user_id: int, new_role: str) -> Membership:
        """Update a member's role in an organization."""
        membership = get_object_or_404(Membership, organization_id=org_id, user_id=target_user_id)
        membership.role = new_role
        membership.save(update_fields=["role"])
        return membership

    @staticmethod
    def remove_member(org_id: int, target_user_id: int) -> None:
        """Remove a member from an organization."""
        membership = get_object_or_404(Membership, organization_id=org_id, user_id=target_user_id)
        membership.delete()
