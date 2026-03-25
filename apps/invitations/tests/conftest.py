import pytest

from apps.organizations.models import Membership, Organization, OrgRole
from apps.users.tests.factories import UserFactory


@pytest.fixture
def receiver(db):
    return UserFactory(
        username="receiver",
        email="receiver@example.com",
        password="testpass123",
    )


@pytest.fixture
def org_with_admin(db, admin_user, member):
    org = Organization.objects.create(name="Sunflower School")
    Membership.objects.create(user=admin_user, organization=org, role=OrgRole.ADMIN)
    Membership.objects.create(user=member, organization=org, role=OrgRole.MEMBER)
    return org
