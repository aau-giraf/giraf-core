"""HTTP client for the giraf-ai image/TTS generation service."""

import base64
import json
import logging
import urllib.request
import urllib.error

from django.conf import settings

from core.exceptions import GirafAIUnavailableError

logger = logging.getLogger(__name__)


def _get_service_token() -> str:
    """Create a minimal JWT for service-to-service auth using the shared secret."""
    import hmac
    import hashlib
    import time

    ninja_jwt = getattr(settings, "NINJA_JWT", {})
    secret = ninja_jwt.get("SIGNING_KEY", getattr(settings, "SECRET_KEY", ""))

    header = base64.urlsafe_b64encode(json.dumps(
        {"alg": "HS256", "typ": "JWT"}
    ).encode()).rstrip(b"=").decode()

    payload = base64.urlsafe_b64encode(json.dumps({
        "sub": "giraf-core-service",
        "org_roles": {},
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }).encode()).rstrip(b"=").decode()

    signing_input = f"{header}.{payload}"
    signature = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()

    return f"{header}.{payload}.{signature}"


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
        token = _get_service_token()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
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
