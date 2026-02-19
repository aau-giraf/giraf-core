"""Business logic for organization operations."""

from django.db import transaction

from apps.organizations.models import Membership, Organization, OrgRole
from apps.users.models import User
from core.exceptions import BadRequestError, ResourceNotFoundError


class OrganizationService:
    @staticmethod
    @transaction.atomic
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
    @transaction.atomic
    def update_organization(*, org_id: int, name: str) -> Organization:
        """Update an organization's name."""
        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            raise ResourceNotFoundError("Organization not found.")
        org.name = name
        org.save(update_fields=["name"])
        return org

    @staticmethod
    @transaction.atomic
    def delete_organization(*, org_id: int) -> None:
        """Delete an organization."""
        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            raise ResourceNotFoundError("Organization not found.")
        org.delete()

    @staticmethod
    def _check_last_owner(org_id: int, membership: Membership) -> None:
        """Raise if this membership is the last owner of the organization."""
        if membership.role == OrgRole.OWNER:
            owner_count = Membership.objects.filter(organization_id=org_id, role=OrgRole.OWNER).count()
            if owner_count <= 1:
                raise BadRequestError("Cannot remove or demote the last owner.")

    @staticmethod
    @transaction.atomic
    def update_member_role(org_id: int, target_user_id: int, new_role: str) -> Membership:
        """Update a member's role in an organization."""
        valid_roles = {r.value for r in OrgRole}
        if new_role not in valid_roles:
            raise BadRequestError(f"Invalid role '{new_role}'. Must be one of: {', '.join(sorted(valid_roles))}.")

        try:
            membership = Membership.objects.get(organization_id=org_id, user_id=target_user_id)
        except Membership.DoesNotExist:
            raise ResourceNotFoundError("Member not found in this organization.")

        OrganizationService._check_last_owner(org_id, membership)

        membership.role = new_role
        membership.save(update_fields=["role"])
        return membership

    @staticmethod
    @transaction.atomic
    def remove_member(org_id: int, target_user_id: int) -> None:
        """Remove a member from an organization."""
        try:
            membership = Membership.objects.get(organization_id=org_id, user_id=target_user_id)
        except Membership.DoesNotExist:
            raise ResourceNotFoundError("Member not found in this organization.")

        OrganizationService._check_last_owner(org_id, membership)

        membership.delete()
