"""Reusable validation utilities."""

import mimetypes
import uuid

from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError

from core.exceptions import BusinessValidationError

_PIL_FORMAT_TO_MIME: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
ALLOWED_IMAGE_TYPES = list(_PIL_FORMAT_TO_MIME.values())
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGE_DIMENSION = 4096


def validate_image_upload(file: UploadedFile) -> str:
    """Validate an uploaded image file. Returns the detected MIME type.

    Opens the file with PIL to detect the actual image format,
    validates it against the allowed types, and checks file size.

    Raises:
        BusinessValidationError: If file type, size, or content is invalid.
    """
    if file.size is not None and file.size > MAX_IMAGE_SIZE:
        raise BusinessValidationError("File size must not exceed 5MB.")

    try:
        img = Image.open(file)
        detected_format = img.format
        img.verify()
        file.seek(0)
    except (UnidentifiedImageError, SyntaxError) as e:
        raise BusinessValidationError("File is not a valid image.") from e

    actual_mime = _PIL_FORMAT_TO_MIME.get(detected_format or "")
    if actual_mime not in ALLOWED_IMAGE_TYPES:
        raise BusinessValidationError("Only JPEG, PNG, and WebP images are allowed.")

    # Re-open to check dimensions (verify() invalidates the image object)
    img = Image.open(file)
    width, height = img.size
    file.seek(0)
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise BusinessValidationError(
            f"Image dimensions must not exceed {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION} pixels."
        )

    return actual_mime


MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB


def _detect_audio_mime(header: bytes) -> str | None:
    """Detect audio MIME type from the first 12 bytes of a file."""
    if len(header) < 4:
        return None

    # MP3 with ID3 tag
    if header[:3] == b"ID3":
        return "audio/mpeg"

    # MP3 MPEG sync word (0xFF followed by 0xE0+ in second byte).
    # Safe against JPEG (0xFF 0xD8): 0xD8 & 0xE0 == 0xC0, not 0xE0.
    if header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
        return "audio/mpeg"

    # WAV: RIFF....WAVE
    if header[:4] == b"RIFF" and len(header) >= 12 and header[8:12] == b"WAVE":
        return "audio/wav"

    # OGG
    if header[:4] == b"OggS":
        return "audio/ogg"

    # FLAC
    if header[:4] == b"fLaC":
        return "audio/flac"

    # AIFF: FORM....AIFF
    if header[:4] == b"FORM" and len(header) >= 12 and header[8:12] == b"AIFF":
        return "audio/aiff"

    # M4A / AAC in MP4 container: ftyp box at offset 4, then check the
    # brand field at offset 8 to avoid matching video MP4/MOV files.
    if len(header) >= 12 and header[4:8] == b"ftyp":
        brand = header[8:12]
        if brand in (b"M4A ", b"M4B ", b"isom", b"mp42"):
            return "audio/mp4"

    return None


def validate_audio_file(file: UploadedFile) -> str:
    """Validate an uploaded audio file. Returns the detected MIME type.

    Reads the file header and checks for known audio format signatures
    (MP3, WAV, OGG, FLAC, AIFF, M4A/AAC).

    Raises:
        BusinessValidationError: If file type, size, or content is invalid.
    """
    if file.size is not None and file.size > MAX_AUDIO_SIZE:
        raise BusinessValidationError("Audio file size must not exceed 10MB.")

    header = file.read(12)
    file.seek(0)

    mime = _detect_audio_mime(header)
    if mime is None:
        raise BusinessValidationError("File is not a recognized audio format.")

    return mime


def sanitized_image_filename(mime_type: str) -> str:
    """Generate a UUID-based filename with the correct extension for a MIME type."""
    ext = mimetypes.guess_extension(mime_type) or ".bin"
    return f"{uuid.uuid4().hex}{ext}"
