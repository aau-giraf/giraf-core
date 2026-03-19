"""Tests for PictogramService."""

import io
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.pictograms.services import PictogramService
from core.exceptions import BusinessValidationError


def _make_test_image(fmt="PNG", name="test.png") -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format=fmt)
    buf.seek(0)
    content_type = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[fmt]
    return SimpleUploadedFile(name, buf.read(), content_type=content_type)


def _make_test_audio(name="test.mp3", size=1024) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"\xff" * size, content_type="audio/mpeg")


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
        image = _make_test_image()
        p = PictogramService.upload_pictogram(name="Valid", image=image, generate_sound=False)
        assert p.pk is not None
        assert p.name == "Valid"

    def test_upload_with_sound_file(self):
        image = _make_test_image()
        sound = _make_test_audio()
        p = PictogramService.upload_pictogram(name="WithSound", image=image, sound=sound, generate_sound=False)
        assert p.pk is not None
        assert p.sound is not None

    def test_upload_rejects_invalid_audio(self):
        image = _make_test_image()
        bad_sound = SimpleUploadedFile("test.txt", b"not audio", content_type="text/plain")
        with pytest.raises(BusinessValidationError, match="Only MP3"):
            PictogramService.upload_pictogram(name="BadSound", image=image, sound=bad_sound)

    def test_upload_rejects_spoofed_mp3(self):
        image = _make_test_image()
        spoofed = SimpleUploadedFile("sneaky.mp3", b"not actually mp3 data", content_type="audio/mpeg")
        with pytest.raises(BusinessValidationError, match="not a valid MP3"):
            PictogramService.upload_pictogram(name="Spoofed", image=image, sound=spoofed)

    def test_upload_rejects_oversized_audio(self):
        image = _make_test_image()
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
        sound = _make_test_audio()
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
