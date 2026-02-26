"""Pydantic schemas for grades."""

from ninja import Schema
from pydantic import Field


class GradeCreateIn(Schema):
    name: str = Field(min_length=1, max_length=255)


class GradeUpdateIn(Schema):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class GradeOut(Schema):
    id: int
    name: str
    organization_id: int


class GradeCitizenAssignIn(Schema):
    citizen_ids: list[int]
