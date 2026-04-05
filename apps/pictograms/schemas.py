"""Pictogram schemas."""

from urllib.parse import urlparse

from ninja import Schema
from pydantic import Field, field_validator


def _validate_image_url(v: str) -> str:
    """Allow empty string or valid http(s) URLs only."""
    if not v:
        return v
    parsed = urlparse(v)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are allowed.")
    return v


class PictogramCreateIn(Schema):
    name: str = Field(min_length=1, max_length=255)
    image_url: str = Field(default="", max_length=500)
    organization_id: int | None = None
    citizen_id: int | None = None
    generate_image: bool = False
    generate_sound: bool = True

    _validate_url = field_validator("image_url")(_validate_image_url)


class PictogramUpdateIn(Schema):
    name: str | None = None
    image_url: str | None = None
    generate_image: bool = False
    regenerate_sound: bool = False

    @field_validator("image_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is not None:
            _validate_image_url(v)
        return v


class PictogramOut(Schema):
    id: int
    name: str
    image_url: str
    sound_url: str
    organization_id: int | None
    citizen_id: int | None

    @staticmethod
    def resolve_image_url(obj):
        return obj.effective_image_url

    @staticmethod
    def resolve_sound_url(obj):
        return obj.effective_sound_url
