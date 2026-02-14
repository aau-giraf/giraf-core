"""Invitation schemas."""
from pydantic import EmailStr

from ninja import Field, Schema


class InvitationCreateIn(Schema):
    receiver_email: EmailStr


class InvitationOut(Schema):
    id: int
    organization_id: int
    organization_name: str = Field(..., alias="organization.name")
    sender_username: str = Field(..., alias="sender.username")
    receiver_username: str = Field(..., alias="receiver.username")
    status: str
