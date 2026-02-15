"""Tests for Organization and Membership models.

Written BEFORE implementation — defines the expected domain behavior.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.users.tests.factories import UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationModel:
    def test_create_organization(self):
        from apps.organizations.models import Organization

        org = Organization.objects.create(name="Sunflower School")
        assert org.pk is not None
        assert org.name == "Sunflower School"
        assert str(org) == "Sunflower School"

    def test_organization_name_required(self):
        from apps.organizations.models import Organization

        with pytest.raises(Exception):
            Organization.objects.create(name="")


@pytest.mark.django_db
class TestMembershipModel:
    def test_add_member_to_org(self):
        from apps.organizations.models import Membership, Organization, OrgRole

        user = UserFactory()
        org = Organization.objects.create(name="Test School")
        membership = Membership.objects.create(user=user, organization=org, role=OrgRole.MEMBER)
        assert membership.pk is not None
        assert membership.role == OrgRole.MEMBER
        assert membership.user == user
        assert membership.organization == org

    def test_membership_roles(self):
        from apps.organizations.models import Membership, Organization, OrgRole

        user = UserFactory()
        org = Organization.objects.create(name="Test School")

        m = Membership.objects.create(user=user, organization=org, role=OrgRole.OWNER)
        assert m.role == OrgRole.OWNER
        assert m.is_owner is True
        assert m.is_admin is True  # Owner is also admin
        assert m.is_member is True  # Owner is also member

    def test_admin_is_also_member(self):
        from apps.organizations.models import Membership, Organization, OrgRole

        user = UserFactory()
        org = Organization.objects.create(name="Test School")
        m = Membership.objects.create(user=user, organization=org, role=OrgRole.ADMIN)
        assert m.is_admin is True
        assert m.is_member is True
        assert m.is_owner is False

    def test_member_is_only_member(self):
        from apps.organizations.models import Membership, Organization, OrgRole

        user = UserFactory()
        org = Organization.objects.create(name="Test School")
        m = Membership.objects.create(user=user, organization=org, role=OrgRole.MEMBER)
        assert m.is_member is True
        assert m.is_admin is False
        assert m.is_owner is False

    def test_user_cannot_have_duplicate_membership(self):
        from apps.organizations.models import Membership, Organization, OrgRole

        user = UserFactory()
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.MEMBER)
        with pytest.raises(IntegrityError):
            Membership.objects.create(user=user, organization=org, role=OrgRole.ADMIN)

    def test_str_representation(self):
        from apps.organizations.models import Membership, Organization, OrgRole

        user = UserFactory(username="jane")
        org = Organization.objects.create(name="Sunflower School")
        m = Membership.objects.create(user=user, organization=org, role=OrgRole.ADMIN)
        assert str(m) == "jane @ Sunflower School (admin)"

    def test_organization_members_queryset(self):
        from apps.organizations.models import Membership, Organization, OrgRole

        org = Organization.objects.create(name="Test School")
        u1 = UserFactory()
        u2 = UserFactory()
        Membership.objects.create(user=u1, organization=org, role=OrgRole.MEMBER)
        Membership.objects.create(user=u2, organization=org, role=OrgRole.ADMIN)
        assert org.memberships.count() == 2

    def test_user_memberships_queryset(self):
        from apps.organizations.models import Membership, Organization, OrgRole

        user = UserFactory()
        org1 = Organization.objects.create(name="School A")
        org2 = Organization.objects.create(name="School B")
        Membership.objects.create(user=user, organization=org1, role=OrgRole.MEMBER)
        Membership.objects.create(user=user, organization=org2, role=OrgRole.OWNER)
        assert user.memberships.count() == 2

    def test_cascade_delete_user_removes_membership(self):
        from apps.organizations.models import Membership, Organization, OrgRole

        user = UserFactory()
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.MEMBER)
        user.delete()
        assert Membership.objects.count() == 0

    def test_cascade_delete_org_removes_membership(self):
        from apps.organizations.models import Membership, Organization, OrgRole

        user = UserFactory()
        org = Organization.objects.create(name="Test School")
        Membership.objects.create(user=user, organization=org, role=OrgRole.MEMBER)
        org.delete()
        assert Membership.objects.count() == 0
