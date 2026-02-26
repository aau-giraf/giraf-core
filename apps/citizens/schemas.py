"""Pydantic schemas for citizens."""

from ninja import Schema
from pydantic import Field


class CitizenCreateIn(Schema):
    first_name: str = Field(min_length=1, max_length=150)
    last_name: str = Field(min_length=1, max_length=150)


class CitizenUpdateIn(Schema):
    first_name: str | None = Field(default=None, min_length=1, max_length=150)
    last_name: str | None = Field(default=None, min_length=1, max_length=150)


class CitizenOut(Schema):
    id: int
    first_name: str
    last_name: str
    organization_id: int
