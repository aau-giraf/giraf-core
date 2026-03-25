"""Factories for pictogram test data."""

import factory

from apps.pictograms.models import Pictogram


class PictogramFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Pictogram

    name = factory.Sequence(lambda n: f"Pictogram {n}")
    image_url = factory.Sequence(lambda n: f"https://example.com/pic{n}.png")
    organization = None
