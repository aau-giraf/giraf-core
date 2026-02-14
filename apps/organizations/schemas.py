"""Pydantic schemas for organizations."""
from ninja import Schema


class OrgCreateIn(Schema):
    name: str


class OrgOut(Schema):
    id: int
    name: str


class MemberOut(Schema):
    id: int
    user_id: int
    username: str
    first_name: str
    last_name: str
    email: str
    role: str

    @staticmethod
    def resolve_username(obj):
        return obj.user.username

    @staticmethod
    def resolve_first_name(obj):
        return obj.user.first_name

    @staticmethod
    def resolve_last_name(obj):
        return obj.user.last_name

    @staticmethod
    def resolve_email(obj):
        return obj.user.email


class OrgUpdateIn(Schema):
    name: str


class MemberRoleUpdateIn(Schema):
    role: str
