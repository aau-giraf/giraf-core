"""Tests for cross-cutting permission utilities.

These test the reusable permission helpers that check org membership/roles.
"""

import pytest

from apps.organizations.models import Membership, Organization, OrgRole
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestGetMembershipOrNone:
    def test_returns_membership_for_member(self):
        from core.permissions import get_membership_or_none

        user = UserFactory()
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.MEMBER)

        result = get_membership_or_none(user, org.id)
        assert result is not None
        assert result.role == OrgRole.MEMBER

    def test_returns_none_for_non_member(self):
        from core.permissions import get_membership_or_none

        user = UserFactory()
        org = Organization.objects.create(name="Test School")

        result = get_membership_or_none(user, org.id)
        assert result is None


@pytest.mark.django_db
class TestCheckRole:
    def test_member_passes_member_check(self):
        from core.permissions import check_role

        user = UserFactory()
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.MEMBER)

        allowed, _ = check_role(user, org.id, min_role=OrgRole.MEMBER)
        assert allowed is True

    def test_member_fails_admin_check(self):
        from core.permissions import check_role

        user = UserFactory()
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.MEMBER)

        allowed, msg = check_role(user, org.id, min_role=OrgRole.ADMIN)
        assert allowed is False

    def test_owner_passes_admin_check(self):
        from core.permissions import check_role

        user = UserFactory()
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)

        allowed, _ = check_role(user, org.id, min_role=OrgRole.ADMIN)
        assert allowed is True

    def test_admin_fails_owner_check(self):
        from core.permissions import check_role

        user = UserFactory()
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.ADMIN)

        allowed, _ = check_role(user, org.id, min_role=OrgRole.OWNER)
        assert allowed is False

    def test_non_member_fails_all_checks(self):
        from core.permissions import check_role

        user = UserFactory()
        org = Organization.objects.create(name="Test School")

        for role in [OrgRole.MEMBER, OrgRole.ADMIN, OrgRole.OWNER]:
            allowed, _ = check_role(user, org.id, min_role=role)
            assert allowed is False
