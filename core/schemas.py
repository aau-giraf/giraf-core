"""Shared schemas for GIRAF Core API."""

from ninja import Schema


class ErrorOut(Schema):
    detail: str
