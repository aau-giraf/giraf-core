"""Shared test utilities for pictogram tests."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def make_test_image(fmt="PNG", name="test.png") -> SimpleUploadedFile:
    """Create a minimal valid image file for testing."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format=fmt)
    buf.seek(0)
    content_type = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[fmt]
    return SimpleUploadedFile(name, buf.read(), content_type=content_type)


def make_test_audio(name="test.mp3", size=1024) -> SimpleUploadedFile:
    """Create a minimal audio file for testing."""
    return SimpleUploadedFile(name, b"\xff" * size, content_type="audio/mpeg")
