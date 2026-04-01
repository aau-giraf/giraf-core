"""Tests for the giraf-ai HTTP client."""

import base64
from unittest.mock import patch

import httpx
import pytest

from core.clients.giraf_ai import GirafAIClient, _get_service_token
from core.exceptions import GirafAIUnavailableError


class TestGetServiceToken:
    @pytest.mark.django_db
    def test_returns_valid_jwt_string(self):
        token = _get_service_token()
        # JWT has 3 dot-separated parts
        parts = token.split(".")
        assert len(parts) == 3

    @pytest.mark.django_db
    def test_token_contains_service_claims(self):
        from ninja_jwt.tokens import AccessToken

        token_str = _get_service_token()
        decoded = AccessToken(token_str)
        assert decoded["sub"] == "giraf-core-service"
        assert decoded["org_roles"] == {}


class TestGirafAIClient:
    def test_raises_when_url_not_configured(self, settings):
        settings.GIRAF_AI_URL = ""
        client = GirafAIClient()
        with pytest.raises(GirafAIUnavailableError, match="not configured"):
            client.generate_image("test")

    @patch("core.clients.giraf_ai._get_service_token", return_value="fake.jwt.token")
    def test_generate_image_returns_bytes(self, mock_token):
        image_b64 = base64.b64encode(b"fake-png-bytes").decode()

        with patch.object(httpx.Client, "post") as mock_post:
            mock_post.return_value = httpx.Response(
                200,
                json={"image_base64": image_b64},
                request=httpx.Request("POST", "http://test/api/v1/generate/image"),
            )
            client = GirafAIClient()
            client.base_url = "http://test"
            result = client.generate_image("cat pictogram")

        assert result == b"fake-png-bytes"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"]["prompt"] == "cat pictogram"

    @patch("core.clients.giraf_ai._get_service_token", return_value="fake.jwt.token")
    def test_generate_tts_returns_bytes(self, mock_token):
        audio_b64 = base64.b64encode(b"fake-mp3-bytes").decode()

        with patch.object(httpx.Client, "post") as mock_post:
            mock_post.return_value = httpx.Response(
                200,
                json={"audio_base64": audio_b64},
                request=httpx.Request("POST", "http://test/api/v1/tts"),
            )
            client = GirafAIClient()
            client.base_url = "http://test"
            result = client.generate_tts("hej verden")

        assert result == b"fake-mp3-bytes"

    @patch("core.clients.giraf_ai._get_service_token", return_value="fake.jwt.token")
    def test_raises_on_http_error(self, mock_token):
        with patch.object(httpx.Client, "post") as mock_post:
            mock_post.return_value = httpx.Response(
                502,
                json={"detail": "bad gateway"},
                request=httpx.Request("POST", "http://test/api/v1/tts"),
            )
            client = GirafAIClient()
            client.base_url = "http://test"
            with pytest.raises(GirafAIUnavailableError, match="HTTP 502"):
                client.generate_tts("test")

    @patch("core.clients.giraf_ai._get_service_token", return_value="fake.jwt.token")
    def test_raises_on_connection_error(self, mock_token):
        with patch.object(httpx.Client, "post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("connection refused")
            client = GirafAIClient()
            client.base_url = "http://test"
            with pytest.raises(GirafAIUnavailableError, match="unreachable"):
                client.generate_image("test")
