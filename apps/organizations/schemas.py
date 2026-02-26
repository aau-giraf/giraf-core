"""Pydantic schemas for organizations."""

from typing import Literal

from ninja import Schema
from pydantic import Field


class OrgCreateIn(Schema):
    name: str = Field(min_length=1, max_length=255)


class OrgOut(Schema):
    id: int
    name: str


class MemberOut(Schema):
    membership_id: int
    user_id: int
    username: str
    first_name: str
    last_name: str
    role: str

    @staticmethod
    def resolve_membership_id(obj):
        return obj.id

    @staticmethod
    def resolve_username(obj):
        return obj.user.username

    @staticmethod
    def resolve_first_name(obj):
        return obj.user.first_name

    @staticmethod
    def resolve_last_name(obj):
        return obj.user.last_name


class OrgUpdateIn(Schema):
    name: str = Field(min_length=1, max_length=255)


class MemberRoleUpdateIn(Schema):
    role: Literal["member", "admin", "owner"]
