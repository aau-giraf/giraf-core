"""HTTP client for the giraf-ai image/TTS generation service."""

import base64
import json
import logging
import urllib.request
import urllib.error

from django.conf import settings

from core.exceptions import GirafAIUnavailableError

logger = logging.getLogger(__name__)


class GirafAIClient:
    """Client for the giraf-ai image/TTS generation service.

    Calls giraf-ai's REST API for image generation and TTS.
    Raises GirafAIUnavailableError when GIRAF_AI_URL is not configured
    or the service is unreachable.
    """

    def __init__(self):
        self.base_url = getattr(settings, "GIRAF_AI_URL", "").rstrip("/")

    def _post(self, path: str, body: dict) -> dict:
        """Make a POST request to giraf-ai and return the parsed JSON response."""
        if not self.base_url:
            raise GirafAIUnavailableError("GIRAF_AI_URL is not configured.")

        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as exc:
            raise GirafAIUnavailableError(
                f"giraf-ai service is unreachable: {exc}"
            ) from exc
        except Exception as exc:
            raise GirafAIUnavailableError(
                f"giraf-ai request failed: {exc}"
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
