"""Reusable validation utilities."""

import mimetypes

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
