"""HTTP client for the giraf-ai image/TTS generation service."""

import base64
import logging

import httpx
from django.conf import settings
from ninja_jwt.tokens import AccessToken

from core.exceptions import GirafAIUnavailableError

logger = logging.getLogger(__name__)

_TIMEOUT = 60.0


def _get_service_token() -> str:
    """Create a short-lived JWT for service-to-service auth."""
    token = AccessToken()
    token["sub"] = "giraf-core-service"
    token["org_roles"] = {}
    return str(token)


class GirafAIClient:
    """Client for the giraf-ai image/TTS generation service.

    Calls giraf-ai's REST API for image generation and TTS.
    Raises GirafAIUnavailableError when GIRAF_AI_URL is not configured
    or the service is unreachable.
    """

    def __init__(self) -> None:
        self.base_url = getattr(settings, "GIRAF_AI_URL", "").rstrip("/")
        self._client = httpx.Client(timeout=_TIMEOUT)

    def _post(self, path: str, body: dict) -> dict:
        """Make a POST request to giraf-ai and return the parsed JSON response."""
        if not self.base_url:
            raise GirafAIUnavailableError("GIRAF_AI_URL is not configured.")

        token = _get_service_token()
        try:
            resp = self._client.post(
                f"{self.base_url}{path}",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result: dict = resp.json()
            return result
        except httpx.HTTPStatusError as exc:
            raise GirafAIUnavailableError(
                f"giraf-ai returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise GirafAIUnavailableError(
                f"giraf-ai service is unreachable: {exc}"
            ) from exc

    def generate_image(self, prompt: str) -> bytes:
        """Generate an image from a text prompt. Returns raw image bytes (PNG)."""
        result = self._post("/api/v1/generate/image", {
            "prompt": prompt,
            "style": "pictogram",
            "format": "png",
        })
        return base64.b64decode(result["image_base64"])

    def generate_tts(self, text: str) -> bytes:
        """Generate TTS audio from text. Returns raw audio bytes (MP3)."""
        result = self._post("/api/v1/tts", {
            "text": text,
            "language": "da",
            "format": "mp3",
        })
        return base64.b64decode(result["audio_base64"])
