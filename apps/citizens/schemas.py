"""Pydantic schemas for citizens."""

from ninja import Schema


class CitizenCreateIn(Schema):
    first_name: str
    last_name: str


class CitizenUpdateIn(Schema):
    first_name: str | None = None
    last_name: str | None = None


class CitizenOut(Schema):
    id: int
    first_name: str
    last_name: str
    organization_id: int
