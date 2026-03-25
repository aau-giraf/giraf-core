"""Factories for citizen test data."""

import factory

from apps.citizens.models import Citizen
from apps.organizations.tests.factories import OrganizationFactory


class CitizenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Citizen

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    organization = factory.SubFactory(OrganizationFactory)
