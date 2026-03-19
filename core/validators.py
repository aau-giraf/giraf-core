"""Reusable validation utilities."""

import mimetypes
import uuid

from PIL import Image

from core.exceptions import BusinessValidationError

ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_image_upload(file) -> str:
    """Validate an uploaded image file. Returns the detected MIME type.

    Checks extension-based MIME type, file size, and PIL image validity.

    Raises:
        BusinessValidationError: If file type, size, or content is invalid.
    """
    mime_type, _ = mimetypes.guess_type(file.name)
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise BusinessValidationError("Only JPEG, PNG, and WebP images are allowed.")

    if file.size > MAX_IMAGE_SIZE:
        raise BusinessValidationError("File size must not exceed 5MB.")

    try:
        Image.open(file).verify()
        file.seek(0)
    except Exception:
        raise BusinessValidationError("File is not a valid image.")

    return mime_type


ALLOWED_AUDIO_TYPES = ["audio/mpeg"]
MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB


def validate_audio_file(file) -> str:
    """Validate an uploaded audio file. Returns the detected MIME type.

    Checks extension-based MIME type and file size.

    Raises:
        BusinessValidationError: If file type or size is invalid.
    """
    mime_type, _ = mimetypes.guess_type(file.name)
    if mime_type not in ALLOWED_AUDIO_TYPES:
        raise BusinessValidationError("Only MP3 audio files are allowed.")

    if file.size > MAX_AUDIO_SIZE:
        raise BusinessValidationError("Audio file size must not exceed 10MB.")

    return mime_type


def sanitized_image_filename(mime_type: str) -> str:
    """Generate a UUID-based filename with the correct extension for a MIME type."""
    ext = mimetypes.guess_extension(mime_type) or ".bin"
    return f"{uuid.uuid4().hex}{ext}"
