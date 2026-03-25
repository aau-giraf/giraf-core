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

    def test_create_api_rejects_no_image_source(self, client, owner, org):
        from conftest import auth_header_for_user

        headers = auth_header_for_user(owner)
        response = client.post(
            "/api/v1/pictograms",
            data={"name": "No Image", "image_url": "", "organization_id": org.id, "generate_sound": False},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 422
