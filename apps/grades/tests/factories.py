"""Factories for grade test data."""

import factory

from apps.grades.models import Grade
from apps.organizations.tests.factories import OrganizationFactory


class GradeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Grade

    name = factory.Sequence(lambda n: f"Class {n}")
    organization = factory.SubFactory(OrganizationFactory)
