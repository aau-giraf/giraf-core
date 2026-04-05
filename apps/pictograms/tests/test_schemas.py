"""Tests for pictogram schema validation, particularly SSRF prevention."""

import socket
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from apps.pictograms.schemas import PictogramCreateIn, PictogramUpdateIn


class TestValidateImageUrl:
    """Test SSRF prevention in image_url validation."""

    def test_empty_string_allowed(self):
        schema = PictogramCreateIn(name="test", image_url="")
        assert schema.image_url == ""

    def test_valid_https_url(self):
        schema = PictogramCreateIn(name="test", image_url="https://example.com/img.png")
        assert schema.image_url == "https://example.com/img.png"

    def test_valid_http_url(self):
        schema = PictogramCreateIn(name="test", image_url="http://example.com/img.png")
        assert schema.image_url == "http://example.com/img.png"

    def test_rejects_file_scheme(self):
        with pytest.raises(ValidationError, match="http and https"):
            PictogramCreateIn(name="test", image_url="file:///etc/passwd")

    def test_rejects_ftp_scheme(self):
        with pytest.raises(ValidationError, match="http and https"):
            PictogramCreateIn(name="test", image_url="ftp://evil.com/file")

    @patch("apps.pictograms.schemas.socket.getaddrinfo")
    def test_rejects_loopback_ip(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0)),
        ]
        with pytest.raises(ValidationError, match="internal/private"):
            PictogramCreateIn(name="test", image_url="http://127.0.0.1/secret")

    @patch("apps.pictograms.schemas.socket.getaddrinfo")
    def test_rejects_private_10_network(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0)),
        ]
        with pytest.raises(ValidationError, match="internal/private"):
            PictogramCreateIn(name="test", image_url="http://internal.corp/data")

    @patch("apps.pictograms.schemas.socket.getaddrinfo")
    def test_rejects_link_local_metadata(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("169.254.169.254", 0)),
        ]
        with pytest.raises(ValidationError, match="internal/private"):
            PictogramCreateIn(name="test", image_url="http://169.254.169.254/latest/meta-data/")

    @patch("apps.pictograms.schemas.socket.getaddrinfo")
    def test_rejects_private_192_168(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.1", 0)),
        ]
        with pytest.raises(ValidationError, match="internal/private"):
            PictogramCreateIn(name="test", image_url="http://192.168.1.1/admin")

    @patch("apps.pictograms.schemas.socket.getaddrinfo")
    def test_rejects_ipv6_loopback(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", 0, 0, 0)),
        ]
        with pytest.raises(ValidationError, match="internal/private"):
            PictogramCreateIn(name="test", image_url="http://ipv6-loopback.evil.com/")

    @patch("apps.pictograms.schemas.socket.getaddrinfo")
    def test_rejects_if_any_resolved_ip_is_private(self, mock_getaddrinfo):
        """If DNS returns both public and private IPs, reject."""
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0)),
        ]
        with pytest.raises(ValidationError, match="internal/private"):
            PictogramCreateIn(name="test", image_url="http://dual-homed.evil.com/")

    @patch("apps.pictograms.schemas.socket.getaddrinfo")
    def test_unresolvable_host_passes(self, mock_getaddrinfo):
        """Unresolvable hostnames pass validation; they'll fail at fetch time."""
        mock_getaddrinfo.side_effect = socket.gaierror("Name or service not known")
        schema = PictogramCreateIn(name="test", image_url="http://doesnt-exist.invalid/img.png")
        assert schema.image_url == "http://doesnt-exist.invalid/img.png"

    @patch("apps.pictograms.schemas.socket.getaddrinfo")
    def test_public_ip_passes(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0)),
        ]
        schema = PictogramCreateIn(name="test", image_url="https://example.com/img.png")
        assert schema.image_url == "https://example.com/img.png"


class TestPictogramUpdateInImageUrl:
    """Verify PictogramUpdateIn also validates image_url."""

    def test_none_allowed(self):
        schema = PictogramUpdateIn(image_url=None)
        assert schema.image_url is None

    def test_empty_string_allowed(self):
        schema = PictogramUpdateIn(image_url="")
        assert schema.image_url == ""

    def test_rejects_file_scheme(self):
        with pytest.raises(ValidationError, match="http and https"):
            PictogramUpdateIn(image_url="file:///etc/passwd")

    @patch("apps.pictograms.schemas.socket.getaddrinfo")
    def test_rejects_private_ip(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0)),
        ]
        with pytest.raises(ValidationError, match="internal/private"):
            PictogramUpdateIn(image_url="http://10.0.0.1/secret")
