"""Factories for invitation test data."""

import factory

from apps.invitations.models import Invitation, InvitationStatus
from apps.organizations.tests.factories import OrganizationFactory
from apps.users.tests.factories import UserFactory


class InvitationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invitation

    organization = factory.SubFactory(OrganizationFactory)
    sender = factory.SubFactory(UserFactory)
    receiver = factory.SubFactory(UserFactory)
    status = InvitationStatus.PENDING
