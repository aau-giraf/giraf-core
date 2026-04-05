"""Pictogram schemas."""

import ipaddress
import socket
from urllib.parse import urlparse

from ninja import Schema
from pydantic import Field, field_validator


def _validate_image_url(v: str) -> str:
    """Allow empty string or valid http(s) URLs with non-private hosts only.

    NOTE: DNS is resolved at validation time. A malicious DNS server could return
    a public IP during validation, then switch to a private IP before the actual
    fetch (DNS rebinding). For full protection, the fetch path should also
    validate resolved IPs. Acceptable risk for this deployment.
    """
    if not v:
        return v
    parsed = urlparse(v)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are allowed.")
    if parsed.hostname:
        try:
            # getaddrinfo resolves both A (IPv4) and AAAA (IPv6) records
            for _family, _type, _proto, _canonname, sockaddr in socket.getaddrinfo(parsed.hostname, None):
                ip = ipaddress.ip_address(sockaddr[0])
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    raise ValueError("URLs pointing to internal/private addresses are not allowed.")
        except socket.gaierror:
            pass  # Unresolvable host will fail at fetch time
    return v


class PictogramCreateIn(Schema):
    name: str = Field(min_length=1, max_length=255)
    image_url: str = Field(default="", max_length=500)
    organization_id: int | None = None
    citizen_id: int | None = None
    generate_image: bool = False
    generate_sound: bool = True

    _validate_url = field_validator("image_url")(_validate_image_url)


class PictogramUpdateIn(Schema):
    name: str | None = None
    image_url: str | None = None
    generate_image: bool = False
    regenerate_sound: bool = False

    @field_validator("image_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is not None:
            _validate_image_url(v)
        return v


class PictogramOut(Schema):
    id: int
    name: str
    image_url: str
    sound_url: str
    organization_id: int | None
    citizen_id: int | None

    @staticmethod
    def resolve_image_url(obj):
        return obj.effective_image_url

    @staticmethod
    def resolve_sound_url(obj):
        return obj.effective_sound_url
