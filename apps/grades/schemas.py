"""Pydantic schemas for grades."""

from ninja import Schema


class GradeCreateIn(Schema):
    name: str


class GradeUpdateIn(Schema):
    name: str | None = None


class GradeOut(Schema):
    id: int
    name: str
    organization_id: int


class GradeCitizenAssignIn(Schema):
    citizen_ids: list[int]
