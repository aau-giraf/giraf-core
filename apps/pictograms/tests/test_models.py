"""Tests for Pictogram model validation and behavior."""

import pytest
from django.core.exceptions import ValidationError

from apps.organizations.models import Organization
from apps.pictograms.tests.utils import make_test_audio, make_test_image


@pytest.mark.django_db
class TestPictogramModel:
    def test_create_org_pictogram(self):
        from apps.pictograms.models import Pictogram

        org = Organization.objects.create(name="Test School")
        p = Pictogram.objects.create(
            name="Happy Face",
            image_url="https://example.com/happy.png",
            organization=org,
        )
        assert p.pk is not None
        assert p.organization == org
        assert str(p) == "Happy Face"

    def test_create_global_pictogram(self):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(
            name="Sad Face",
            image_url="https://example.com/sad.png",
            organization=None,
        )
        assert p.pk is not None
        assert p.organization is None

    def test_effective_sound_url_empty_when_no_sound(self):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="NoSound", image_url="https://example.com/pic.png")
        assert p.effective_sound_url == ""

    def test_effective_sound_url_returns_file_url(self):
        from apps.pictograms.models import Pictogram

        sound = make_test_audio()
        p = Pictogram.objects.create(name="WithSound", image_url="https://example.com/pic.png", sound=sound)
        assert p.effective_sound_url != ""
        assert "mp3" in p.effective_sound_url

    def test_clean_still_requires_image(self):
        from apps.pictograms.models import Pictogram

        with pytest.raises(ValidationError):
            Pictogram.objects.create(name="No Image", sound=make_test_audio())


@pytest.mark.django_db
class TestPictogramValidation:
    def test_pictogram_requires_image_source(self):
        from apps.pictograms.models import Pictogram

        with pytest.raises(ValidationError):
            Pictogram.objects.create(name="No Image", image_url="", image=None)

    def test_pictogram_with_url_only_valid(self):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="URL Only", image_url="https://example.com/pic.png")
        assert p.pk is not None

    def test_pictogram_with_file_only_valid(self):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="File Only", image=make_test_image())
        assert p.pk is not None


@pytest.mark.django_db
class TestPictogramCitizenScope:
    def test_create_citizen_scoped_pictogram(self):
        from apps.citizens.models import Citizen
        from apps.pictograms.models import Pictogram

        org = Organization.objects.create(name="Test School")
        citizen = Citizen.objects.create(first_name="Alice", last_name="Test", organization=org)
        p = Pictogram.objects.create(
            name="Alice Zoo",
            image_url="https://example.com/zoo.png",
            organization=org,
            citizen=citizen,
        )
        assert p.pk is not None
        assert p.citizen == citizen
        assert p.organization == org

    def test_citizen_scoped_requires_organization(self):
        from apps.citizens.models import Citizen
        from apps.pictograms.models import Pictogram

        org = Organization.objects.create(name="Test School")
        citizen = Citizen.objects.create(first_name="Alice", last_name="Test", organization=org)
        with pytest.raises(ValidationError, match="organization"):
            Pictogram.objects.create(
                name="Bad",
                image_url="https://example.com/pic.png",
                organization=None,
                citizen=citizen,
            )

    def test_citizen_must_belong_to_pictogram_org(self):
        from apps.citizens.models import Citizen
        from apps.pictograms.models import Pictogram

        org_a = Organization.objects.create(name="School A")
        org_b = Organization.objects.create(name="School B")
        citizen = Citizen.objects.create(first_name="Alice", last_name="Test", organization=org_a)
        with pytest.raises(ValidationError, match="organization"):
            Pictogram.objects.create(
                name="Wrong Org",
                image_url="https://example.com/pic.png",
                organization=org_b,
                citizen=citizen,
            )

    def test_existing_global_and_org_pictograms_unaffected(self):
        from apps.pictograms.models import Pictogram

        org = Organization.objects.create(name="Test School")
        g = Pictogram.objects.create(name="Global", image_url="https://g.com/g.png", organization=None)
        o = Pictogram.objects.create(name="Org", image_url="https://o.com/o.png", organization=org)
        assert g.citizen is None
        assert o.citizen is None
