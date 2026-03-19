"""Pictogram schemas."""

from ninja import Schema
from pydantic import Field


class PictogramCreateIn(Schema):
    name: str = Field(min_length=1, max_length=255)
    image_url: str = Field(default="", max_length=500)
    organization_id: int | None = None
    generate_image: bool = False
    generate_sound: bool = True


class PictogramUpdateIn(Schema):
    name: str | None = None
    image_url: str | None = None
    generate_image: bool = False
    regenerate_sound: bool = False


class PictogramOut(Schema):
    id: int
    name: str
    image_url: str
    sound_url: str
    organization_id: int | None

    @staticmethod
    def resolve_image_url(obj):
        return obj.effective_image_url

    @staticmethod
    def resolve_sound_url(obj):
        return obj.effective_sound_url
