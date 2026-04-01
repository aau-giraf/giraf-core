"""Tests for PictogramService."""

import io
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.pictograms.services import PictogramService
from apps.pictograms.tests.utils import make_test_audio, make_test_image
from core.exceptions import BusinessValidationError


@pytest.mark.django_db
class TestPictogramServiceUpload:
    def test_upload_invalid_mime_type(self):
        file = SimpleUploadedFile("test.txt", b"not an image", content_type="text/plain")
        with pytest.raises(BusinessValidationError, match="Only JPEG, PNG, and WebP"):
            PictogramService.upload_pictogram(name="Bad", image=file)

    def test_upload_oversized_file(self):
        buf = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buf, format="PNG")
        buf.seek(0)
        file = SimpleUploadedFile("big.png", buf.read() + b"\x00" * (6 * 1024 * 1024), content_type="image/png")
        with pytest.raises(BusinessValidationError, match="5MB"):
            PictogramService.upload_pictogram(name="Big", image=file)

    def test_upload_corrupted_image(self):
        file = SimpleUploadedFile("fake.png", b"not actually an image", content_type="image/png")
        with pytest.raises(BusinessValidationError, match="not a valid image"):
            PictogramService.upload_pictogram(name="Fake", image=file)

    def test_upload_valid_image_succeeds(self):
        image = make_test_image()
        p = PictogramService.upload_pictogram(name="Valid", image=image, generate_sound=False)
        assert p.pk is not None
        assert p.name == "Valid"

    def test_upload_with_sound_file(self):
        image = make_test_image()
        sound = make_test_audio()
        p = PictogramService.upload_pictogram(name="WithSound", image=image, sound=sound, generate_sound=False)
        assert p.pk is not None
        assert p.sound is not None

    def test_upload_rejects_invalid_audio(self):
        image = make_test_image()
        bad_sound = SimpleUploadedFile("test.txt", b"not audio", content_type="text/plain")
        with pytest.raises(BusinessValidationError, match="Only MP3"):
            PictogramService.upload_pictogram(name="BadSound", image=image, sound=bad_sound)

    def test_upload_rejects_spoofed_mp3(self):
        image = make_test_image()
        spoofed = SimpleUploadedFile("sneaky.mp3", b"not actually mp3 data", content_type="audio/mpeg")
        with pytest.raises(BusinessValidationError, match="not a valid MP3"):
            PictogramService.upload_pictogram(name="Spoofed", image=image, sound=spoofed)

    def test_upload_rejects_oversized_audio(self):
        image = make_test_image()
        big_sound = SimpleUploadedFile("big.mp3", b"\xff" * (11 * 1024 * 1024), content_type="audio/mpeg")
        with pytest.raises(BusinessValidationError, match="10MB"):
            PictogramService.upload_pictogram(name="BigSound", image=image, sound=big_sound)


@pytest.mark.django_db
class TestPictogramServiceCreate:
    def test_create_with_generate_sound_skips_gracefully(self):
        """When AI is unavailable, create still succeeds without sound."""
        p = PictogramService.create_pictogram(
            name="Test", image_url="https://example.com/img.png", generate_sound=True
        )
        assert p.pk is not None
        assert not p.sound

    def test_create_with_generate_image_skips_gracefully(self):
        """When AI is unavailable, create still succeeds without generated image."""
        p = PictogramService.create_pictogram(
            name="Test", image_url="https://example.com/img.png", generate_image=True, generate_sound=False
        )
        assert p.pk is not None

    @patch("apps.pictograms.services.GirafAIClient")
    def test_create_with_generate_sound_calls_ai(self, mock_client):
        mock_instance = mock_client.return_value
        mock_instance.generate_tts.return_value = b"\xff\xfb\x90\x00" * 100

        p = PictogramService.create_pictogram(
            name="AI Sound", image_url="https://example.com/img.png", generate_sound=True
        )
        assert p.pk is not None
        mock_instance.generate_tts.assert_called_once_with("AI Sound")
        assert p.sound

    @patch("apps.pictograms.services.GirafAIClient")
    def test_create_with_generate_image_calls_ai(self, mock_client):
        mock_instance = mock_client.return_value
        # Return minimal PNG bytes
        buf = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buf, format="PNG")
        mock_instance.generate_image.return_value = buf.getvalue()

        p = PictogramService.create_pictogram(
            name="AI Image", image_url="https://example.com/fallback.png", generate_image=True, generate_sound=False
        )
        assert p.pk is not None
        mock_instance.generate_image.assert_called_once_with("AI Image")
        assert p.image


@pytest.mark.django_db
class TestPictogramServiceUpdate:
    def test_update_name(self):
        p = PictogramService.create_pictogram(
            name="Old", image_url="https://example.com/img.png", generate_sound=False
        )
        updated = PictogramService.update_pictogram(pictogram_id=p.pk, name="New")
        assert updated.name == "New"

    def test_update_image_url(self):
        p = PictogramService.create_pictogram(
            name="Test", image_url="https://example.com/old.png", generate_sound=False
        )
        updated = PictogramService.update_pictogram(pictogram_id=p.pk, image_url="https://example.com/new.png")
        assert updated.image_url == "https://example.com/new.png"

    def test_update_sound_file(self):
        p = PictogramService.create_pictogram(
            name="Test", image_url="https://example.com/img.png", generate_sound=False
        )
        sound = make_test_audio()
        updated = PictogramService.update_pictogram(pictogram_id=p.pk, sound=sound)
        assert updated.sound

    def test_update_regenerate_sound_skips_gracefully(self):
        """When AI is unavailable, regenerate_sound doesn't fail."""
        p = PictogramService.create_pictogram(
            name="Test", image_url="https://example.com/img.png", generate_sound=False
        )
        updated = PictogramService.update_pictogram(pictogram_id=p.pk, regenerate_sound=True)
        assert updated.pk == p.pk


@pytest.mark.django_db
class TestPictogramServiceErrors:
    def test_get_pictogram_not_found(self):
        from core.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError):
            PictogramService.get_pictogram(99999)

    def test_list_pictograms_global_only(self):
        from apps.organizations.models import Organization

        org = Organization.objects.create(name="Test School")
        PictogramService.create_pictogram(name="Global", image_url="http://g.png", generate_sound=False)
        PictogramService.create_pictogram(
            name="OrgOnly", image_url="http://o.png", organization_id=org.id, generate_sound=False
        )

        results = list(PictogramService.list_pictograms(None))
        names = [p.name for p in results]
        assert "Global" in names
        assert "OrgOnly" not in names


@pytest.mark.django_db
class TestPictogramServiceSearch:
    def test_search_filters_by_name(self):
        PictogramService.create_pictogram(name="Cat", image_url="http://c.png", generate_sound=False)
        PictogramService.create_pictogram(name="Dog", image_url="http://d.png", generate_sound=False)
        PictogramService.create_pictogram(name="Caterpillar", image_url="http://cp.png", generate_sound=False)

        results = list(PictogramService.list_pictograms(search="cat"))
        names = [p.name for p in results]
        assert "Cat" in names
        assert "Caterpillar" in names
        assert "Dog" not in names

    def test_search_is_case_insensitive(self):
        PictogramService.create_pictogram(name="cat", image_url="http://c.png", generate_sound=False)

        results = list(PictogramService.list_pictograms(search="CAT"))
        assert len(results) == 1
        assert results[0].name == "cat"

    def test_search_no_match_returns_empty(self):
        PictogramService.create_pictogram(name="Cat", image_url="http://c.png", generate_sound=False)

        results = list(PictogramService.list_pictograms(search="xyz"))
        assert len(results) == 0

    def test_search_with_org_filters_both(self):
        from apps.organizations.models import Organization

        org = Organization.objects.create(name="Test School")
        PictogramService.create_pictogram(name="Cat Global", image_url="http://cg.png", generate_sound=False)
        PictogramService.create_pictogram(
            name="Cat Org", image_url="http://co.png", organization_id=org.id, generate_sound=False
        )
        PictogramService.create_pictogram(
            name="Dog Org", image_url="http://do.png", organization_id=org.id, generate_sound=False
        )

        results = list(PictogramService.list_pictograms(organization_id=org.id, search="cat"))
        names = [p.name for p in results]
        assert "Cat Global" in names
        assert "Cat Org" in names
        assert "Dog Org" not in names


@pytest.mark.django_db
class TestPictogramServiceCitizenScope:
    def _make_org_and_citizen(self):
        from apps.citizens.models import Citizen
        from apps.organizations.models import Organization

        org = Organization.objects.create(name="Test School")
        citizen = Citizen.objects.create(first_name="Alice", last_name="Test", organization=org)
        return org, citizen

    def test_create_citizen_scoped_pictogram(self):
        org, citizen = self._make_org_and_citizen()
        p = PictogramService.create_pictogram(
            name="Alice Zoo",
            image_url="http://zoo.png",
            organization_id=org.id,
            citizen_id=citizen.id,
            generate_sound=False,
        )
        assert p.pk is not None
        assert p.citizen_id == citizen.id
        assert p.organization_id == org.id

    def test_create_citizen_scoped_requires_org(self):
        _org, citizen = self._make_org_and_citizen()
        with pytest.raises(BusinessValidationError, match="require"):
            PictogramService.create_pictogram(
                name="Bad",
                image_url="http://pic.png",
                citizen_id=citizen.id,
                generate_sound=False,
            )

    def test_create_citizen_scoped_wrong_org(self):
        from apps.organizations.models import Organization

        _org_a, citizen = self._make_org_and_citizen()
        org_b = Organization.objects.create(name="Other School")
        with pytest.raises(BusinessValidationError, match="does not belong"):
            PictogramService.create_pictogram(
                name="Wrong",
                image_url="http://pic.png",
                organization_id=org_b.id,
                citizen_id=citizen.id,
                generate_sound=False,
            )

    def test_create_citizen_not_found(self):
        from core.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError):
            PictogramService.create_pictogram(
                name="Ghost",
                image_url="http://pic.png",
                organization_id=1,
                citizen_id=99999,
                generate_sound=False,
            )

    def test_upload_citizen_scoped(self):
        org, citizen = self._make_org_and_citizen()
        image = make_test_image()
        p = PictogramService.upload_pictogram(
            name="Upload",
            image=image,
            organization_id=org.id,
            citizen_id=citizen.id,
            generate_sound=False,
        )
        assert p.pk is not None
        assert p.citizen_id == citizen.id

    def test_list_for_citizen_returns_three_tiers(self):
        org, citizen = self._make_org_and_citizen()
        PictogramService.create_pictogram(name="Global", image_url="http://g.png", generate_sound=False)
        PictogramService.create_pictogram(
            name="Org", image_url="http://o.png", organization_id=org.id, generate_sound=False
        )
        PictogramService.create_pictogram(
            name="Citizen",
            image_url="http://c.png",
            organization_id=org.id,
            citizen_id=citizen.id,
            generate_sound=False,
        )

        results = list(PictogramService.list_pictograms(organization_id=org.id, citizen_id=citizen.id))
        names = [p.name for p in results]
        assert "Global" in names
        assert "Org" in names
        assert "Citizen" in names

    def test_list_for_citizen_excludes_other_citizen(self):
        from apps.citizens.models import Citizen

        org, alice = self._make_org_and_citizen()
        bob = Citizen.objects.create(first_name="Bob", last_name="Test", organization=org)
        PictogramService.create_pictogram(
            name="Alice Pic",
            image_url="http://a.png",
            organization_id=org.id,
            citizen_id=alice.id,
            generate_sound=False,
        )
        PictogramService.create_pictogram(
            name="Bob Pic",
            image_url="http://b.png",
            organization_id=org.id,
            citizen_id=bob.id,
            generate_sound=False,
        )

        results = list(PictogramService.list_pictograms(organization_id=org.id, citizen_id=alice.id))
        names = [p.name for p in results]
        assert "Alice Pic" in names
        assert "Bob Pic" not in names

    def test_list_for_org_excludes_citizen_scoped(self):
        org, citizen = self._make_org_and_citizen()
        PictogramService.create_pictogram(
            name="Org Pic", image_url="http://o.png", organization_id=org.id, generate_sound=False
        )
        PictogramService.create_pictogram(
            name="Citizen Pic",
            image_url="http://c.png",
            organization_id=org.id,
            citizen_id=citizen.id,
            generate_sound=False,
        )

        results = list(PictogramService.list_pictograms(organization_id=org.id))
        names = [p.name for p in results]
        assert "Org Pic" in names
        assert "Citizen Pic" not in names

    def test_list_global_excludes_citizen_scoped(self):
        org, citizen = self._make_org_and_citizen()
        PictogramService.create_pictogram(name="Global", image_url="http://g.png", generate_sound=False)
        PictogramService.create_pictogram(
            name="Citizen Pic",
            image_url="http://c.png",
            organization_id=org.id,
            citizen_id=citizen.id,
            generate_sound=False,
        )

        results = list(PictogramService.list_pictograms())
        names = [p.name for p in results]
        assert "Global" in names
        assert "Citizen Pic" not in names
