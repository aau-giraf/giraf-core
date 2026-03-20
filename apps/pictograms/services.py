"""Business logic for pictogram operations."""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, QuerySet

from apps.pictograms.models import Pictogram
from core.clients.giraf_ai import GirafAIClient
from core.exceptions import (
    BusinessValidationError,
    GirafAIUnavailableError,
    ResourceNotFoundError,
)
from core.validators import validate_audio_file, validate_image_upload

logger = logging.getLogger(__name__)


class PictogramService:
    @staticmethod
    def _get_pictogram_or_raise(pictogram_id: int) -> Pictogram:
        try:
            return Pictogram.objects.get(id=pictogram_id)
        except Pictogram.DoesNotExist:
            raise ResourceNotFoundError(f"Pictogram {pictogram_id} not found.")

    @staticmethod
    def _try_generate_sound(pictogram: Pictogram) -> None:
        """Attempt to generate TTS sound for a pictogram. Fails gracefully."""
        try:
            client = GirafAIClient()
            audio_bytes = client.generate_tts(pictogram.name)
            pictogram.sound.save(f"{pictogram.pk}.mp3", ContentFile(audio_bytes), save=True)
        except GirafAIUnavailableError:
            logger.warning("giraf-ai unavailable — skipping TTS for pictogram %s", pictogram.pk)
        except Exception:
            logger.exception("Unexpected error generating TTS for pictogram %s", pictogram.pk)

    @staticmethod
    def _try_generate_image(pictogram: Pictogram, prompt: str) -> None:
        """Attempt to generate an image for a pictogram. Fails gracefully."""
        try:
            client = GirafAIClient()
            image_bytes = client.generate_image(prompt)
            pictogram.image.save(f"{pictogram.pk}.png", ContentFile(image_bytes), save=True)
        except GirafAIUnavailableError:
            logger.warning("giraf-ai unavailable — skipping image generation for pictogram %s", pictogram.pk)
        except Exception:
            logger.exception("Unexpected error generating image for pictogram %s", pictogram.pk)

    @staticmethod
    @transaction.atomic
    def create_pictogram(
        *,
        name: str,
        image_url: str = "",
        organization_id: int | None = None,
        generate_image: bool = False,
        generate_sound: bool = True,
    ) -> Pictogram:
        if generate_image and not image_url:
            # Skip model validation — image will be populated by AI generation.
            pictogram = Pictogram(
                name=name,
                image_url=image_url,
                organization_id=organization_id,
            )
            super(Pictogram, pictogram).save()

            PictogramService._try_generate_image(pictogram, name)

            # If AI generation failed, the pictogram has no image — validate now.
            if not pictogram.image and not pictogram.image_url:
                pictogram.delete()
                raise BusinessValidationError(
                    "Image generation failed and no image_url was provided."
                )
        else:
            try:
                pictogram = Pictogram.objects.create(
                    name=name,
                    image_url=image_url,
                    organization_id=organization_id,
                )
            except DjangoValidationError as e:
                raise BusinessValidationError(" ".join(e.messages))

            if generate_image:
                PictogramService._try_generate_image(pictogram, name)

        if generate_sound:
            PictogramService._try_generate_sound(pictogram)

        return pictogram

    @staticmethod
    def list_pictograms(organization_id: int | None = None) -> QuerySet[Pictogram]:
        if organization_id:
            return Pictogram.objects.filter(Q(organization_id=organization_id) | Q(organization__isnull=True))
        return Pictogram.objects.filter(organization__isnull=True)

    @staticmethod
    def get_pictogram(pictogram_id: int) -> Pictogram:
        return PictogramService._get_pictogram_or_raise(pictogram_id)

    @staticmethod
    @transaction.atomic
    def upload_pictogram(
        *,
        name: str,
        image,
        organization_id: int | None = None,
        sound=None,
        generate_sound: bool = True,
    ) -> Pictogram:
        """Upload a pictogram with an image file and optional sound file.

        Raises:
            BusinessValidationError: If file type or size is invalid.
        """
        validate_image_upload(image)
        if sound is not None:
            validate_audio_file(sound)

        pictogram = Pictogram.objects.create(
            name=name,
            image=image,
            sound=sound,
            organization_id=organization_id,
        )

        if sound is None and generate_sound:
            PictogramService._try_generate_sound(pictogram)

        return pictogram

    @staticmethod
    @transaction.atomic
    def update_pictogram(
        *,
        pictogram_id: int,
        name: str | None = None,
        image_url: str | None = None,
        generate_image: bool = False,
        regenerate_sound: bool = False,
        sound=None,
    ) -> Pictogram:
        """Update a pictogram's fields. Supports name, image_url, sound upload, and AI regeneration."""
        pictogram = PictogramService._get_pictogram_or_raise(pictogram_id)

        if name is not None:
            pictogram.name = name
        if image_url is not None:
            pictogram.image_url = image_url

        if sound is not None:
            validate_audio_file(sound)
            pictogram.sound = sound

        pictogram.save()

        if generate_image:
            PictogramService._try_generate_image(pictogram, pictogram.name)

        if regenerate_sound and sound is None:
            PictogramService._try_generate_sound(pictogram)

        return pictogram

    @staticmethod
    @transaction.atomic
    def delete_pictogram(*, pictogram_id: int) -> None:
        pictogram = PictogramService._get_pictogram_or_raise(pictogram_id)
        pictogram.delete()
