"""Pictogram schemas."""

from ninja import Schema
from pydantic import Field


class PictogramCreateIn(Schema):
    name: str = Field(min_length=1, max_length=255)
    image_url: str = Field(max_length=500)
    organization_id: int | None = None


class PictogramOut(Schema):
    id: int
    name: str
    image_url: str
    organization_id: int | None

    @staticmethod
    def resolve_image_url(obj):
        return obj.effective_image_url
