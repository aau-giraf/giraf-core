"""Tests for file upload validators."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from core.exceptions import BusinessValidationError
from core.validators import validate_audio_file, validate_image_upload


class TestValidateImageUpload:
    @staticmethod
    def _make_image(fmt: str = "PNG", name: str = "test.png") -> SimpleUploadedFile:
        buf = io.BytesIO()
        Image.new("RGB", (1, 1)).save(buf, format=fmt)
        buf.seek(0)
        return SimpleUploadedFile(name, buf.read(), content_type=f"image/{fmt.lower()}")

    def test_valid_png(self):
        f = self._make_image("PNG", "photo.png")
        assert validate_image_upload(f) == "image/png"

    def test_valid_jpeg(self):
        f = self._make_image("JPEG", "photo.jpg")
        assert validate_image_upload(f) == "image/jpeg"

    def test_valid_webp(self):
        f = self._make_image("WEBP", "photo.webp")
        assert validate_image_upload(f) == "image/webp"

    def test_detects_actual_format_ignoring_extension(self):
        """A JPEG file named .png should be detected as JPEG, not PNG."""
        f = self._make_image("JPEG", "sneaky.png")
        assert validate_image_upload(f) == "image/jpeg"

    def test_rejects_disallowed_format(self):
        buf = io.BytesIO()
        Image.new("RGB", (1, 1)).save(buf, format="BMP")
        buf.seek(0)
        f = SimpleUploadedFile("image.bmp", buf.read(), content_type="image/bmp")
        with pytest.raises(BusinessValidationError, match="JPEG, PNG, and WebP"):
            validate_image_upload(f)

    def test_rejects_non_image(self):
        f = SimpleUploadedFile("evil.png", b"not an image at all")
        with pytest.raises(BusinessValidationError, match="not a valid image"):
            validate_image_upload(f)

    def test_rejects_oversized_file(self):
        f = self._make_image()
        f.size = 6 * 1024 * 1024  # fake 6MB
        with pytest.raises(BusinessValidationError, match="5MB"):
            validate_image_upload(f)


class TestValidateAudioFile:
    def test_valid_mp3_with_id3(self):
        content = b"ID3" + b"\x00" * 100
        f = SimpleUploadedFile("audio.mp3", content, content_type="audio/mpeg")
        assert validate_audio_file(f) == "audio/mpeg"

    def test_valid_mp3_with_sync_word(self):
        content = b"\xff\xfb" + b"\x00" * 100
        f = SimpleUploadedFile("audio.mp3", content, content_type="audio/mpeg")
        assert validate_audio_file(f) == "audio/mpeg"

    def test_valid_wav(self):
        content = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 100
        f = SimpleUploadedFile("audio.wav", content, content_type="audio/wav")
        assert validate_audio_file(f) == "audio/wav"

    def test_valid_ogg(self):
        content = b"OggS" + b"\x00" * 100
        f = SimpleUploadedFile("audio.ogg", content, content_type="audio/ogg")
        assert validate_audio_file(f) == "audio/ogg"

    def test_valid_flac(self):
        content = b"fLaC" + b"\x00" * 100
        f = SimpleUploadedFile("audio.flac", content, content_type="audio/flac")
        assert validate_audio_file(f) == "audio/flac"

    def test_valid_aiff(self):
        content = b"FORM" + b"\x00" * 4 + b"AIFF" + b"\x00" * 100
        f = SimpleUploadedFile("audio.aiff", content, content_type="audio/aiff")
        assert validate_audio_file(f) == "audio/aiff"

    def test_valid_m4a(self):
        content = b"\x00" * 4 + b"ftyp" + b"\x00" * 100
        f = SimpleUploadedFile("audio.m4a", content, content_type="audio/mp4")
        assert validate_audio_file(f) == "audio/mp4"

    def test_rejects_invalid_content(self):
        f = SimpleUploadedFile("audio.mp3", b"not audio data at all")
        with pytest.raises(BusinessValidationError, match="not a recognized audio"):
            validate_audio_file(f)

    def test_rejects_too_short(self):
        f = SimpleUploadedFile("audio.mp3", b"ab")
        with pytest.raises(BusinessValidationError, match="not a recognized audio"):
            validate_audio_file(f)

    def test_rejects_oversized_file(self):
        content = b"ID3" + b"\x00" * 100
        f = SimpleUploadedFile("audio.mp3", content, content_type="audio/mpeg")
        f.size = 11 * 1024 * 1024
        with pytest.raises(BusinessValidationError, match="10MB"):
            validate_audio_file(f)
