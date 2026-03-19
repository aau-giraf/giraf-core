"""Stubbed client for the giraf-ai service."""

import logging

from django.conf import settings

from core.exceptions import GirafAIUnavailableError

logger = logging.getLogger(__name__)


class GirafAIClient:
    """Client for the giraf-ai image/TTS generation service.

    Currently stubbed — all methods raise GirafAIUnavailableError.
    Will be implemented when giraf-ai is deployed.
    """

    def __init__(self):
        self.base_url = getattr(settings, "GIRAF_AI_URL", "")

    def generate_image(self, prompt: str) -> bytes:
        """Generate an image from a text prompt. Returns raw image bytes (PNG)."""
        raise GirafAIUnavailableError("giraf-ai service is not yet available.")

    def generate_tts(self, text: str) -> bytes:
        """Generate TTS audio from text. Returns raw audio bytes (MP3)."""
        raise GirafAIUnavailableError("giraf-ai service is not yet available.")
