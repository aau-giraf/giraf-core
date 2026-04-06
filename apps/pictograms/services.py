"""Business logic for pictogram operations."""

import logging
import uuid

import httpx
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Q, QuerySet

from apps.pictograms.models import Pictogram
from core.clients.giraf_ai import GirafAIClient
from core.exceptions import (
    BusinessValidationError,
    GirafAIUnavailableError,
    ResourceNotFoundError,
)
from core.validators import resize_image, validate_audio_file, validate_image_upload

logger = logging.getLogger(__name__)


class PictogramService:
    @staticmethod
    def _try_generate_sound(pictogram: Pictogram) -> None:
        """Attempt to generate TTS sound for a pictogram. Fails gracefully."""
        try:
            client = GirafAIClient()
            audio_bytes = client.generate_tts(pictogram.name)
            pictogram.sound.save(f"{pictogram.pk}.wav", ContentFile(audio_bytes), save=True)
        except GirafAIUnavailableError:
            logger.warning("giraf-ai unavailable — skipping TTS for pictogram %s", pictogram.pk)
        except (httpx.HTTPError, ValueError, KeyError):
            logger.exception("Unexpected error generating TTS for pictogram %s", pictogram.pk)

    @staticmethod
    def _validate_citizen_org(citizen_id: int, organization_id: int | None) -> None:
        """Validate that a citizen exists and belongs to the specified organization."""
        from apps.citizens.services import CitizenService

        citizen = CitizenService.get_citizen(citizen_id)  # raises ResourceNotFoundError
        if not organization_id:
            raise BusinessValidationError("Citizen-scoped pictograms require an organization.")
        if citizen.organization_id != organization_id:
            raise BusinessValidationError("Citizen does not belong to the specified organization.")

    @staticmethod
    def _try_generate_image_bytes(prompt: str) -> bytes | None:
        """Attempt to generate image bytes from giraf-ai. Returns None on failure."""
        try:
            client = GirafAIClient()
            return client.generate_image(prompt)
        except GirafAIUnavailableError as exc:
            logger.warning("giraf-ai unavailable for image generation: %s", exc)
            return None
        except (httpx.HTTPError, ValueError, KeyError):
            logger.exception("Unexpected error generating image for prompt: %s", prompt)
            return None

    @staticmethod
    @transaction.atomic
    def create_pictogram(
        *,
        name: str,
        image_url: str = "",
        organization_id: int | None = None,
        citizen_id: int | None = None,
        generate_image: bool = False,
        generate_sound: bool = True,
    ) -> Pictogram:
        if citizen_id:
            PictogramService._validate_citizen_org(citizen_id, organization_id)

        # If AI image generation is requested without a fallback URL,
        # generate the image first so the model never hits the DB without one.
        image_content: ContentFile | None = None
        if generate_image:
            image_bytes = PictogramService._try_generate_image_bytes(name)
            if image_bytes:
                image_content = ContentFile(image_bytes, name=f"{uuid.uuid4().hex}.png")

        if generate_image and not image_url and not image_content:
            raise BusinessValidationError(
                "Image generation failed and no image_url was provided."
            )

        try:
            pictogram = Pictogram.objects.create(
                name=name,
                image_url=image_url,
                image=image_content,
                organization_id=organization_id,
                citizen_id=citizen_id,
            )
        except DjangoValidationError as e:
            raise BusinessValidationError(" ".join(e.messages)) from e

        if generate_sound:
            PictogramService._try_generate_sound(pictogram)

        return pictogram

    @staticmethod
    def list_pictograms(
        organization_id: int | None = None,
        citizen_id: int | None = None,
        search: str | None = None,
    ) -> QuerySet[Pictogram]:
        if citizen_id:
            # Three-tier: global + org + citizen
            qs = Pictogram.objects.filter(
                Q(organization__isnull=True, citizen__isnull=True)
                | Q(organization_id=organization_id, citizen__isnull=True)
                | Q(organization_id=organization_id, citizen_id=citizen_id)
            )
        elif organization_id:
            # Two-tier: global + org (exclude citizen-scoped)
            qs = Pictogram.objects.filter(
                Q(organization_id=organization_id, citizen__isnull=True)
                | Q(organization__isnull=True, citizen__isnull=True)
            )
        else:
            qs = Pictogram.objects.filter(organization__isnull=True, citizen__isnull=True)
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    @staticmethod
    def get_pictogram(pictogram_id: int) -> Pictogram:
        try:
            return Pictogram.objects.get(id=pictogram_id)
        except Pictogram.DoesNotExist as e:
            raise ResourceNotFoundError(f"Pictogram {pictogram_id} not found.") from e

    @staticmethod
    @transaction.atomic
    def upload_pictogram(
        *,
        name: str,
        image: UploadedFile,
        organization_id: int | None = None,
        citizen_id: int | None = None,
        sound: UploadedFile | None = None,
        generate_sound: bool = True,
    ) -> Pictogram:
        """Upload a pictogram with an image file and optional sound file.

        Raises:
            BusinessValidationError: If file type or size is invalid.
        """
        if citizen_id:
            PictogramService._validate_citizen_org(citizen_id, organization_id)

        mime_type = validate_image_upload(image)
        image = resize_image(image, max_dimension=512, mime_type=mime_type)
        if sound is not None:
            validate_audio_file(sound)

        pictogram = Pictogram.objects.create(
            name=name,
            image=image,
            sound=sound,
            organization_id=organization_id,
            citizen_id=citizen_id,
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
        sound: UploadedFile | None = None,
    ) -> Pictogram:
        """Update a pictogram's fields. Supports name, image_url, sound upload, and AI regeneration."""
        pictogram = PictogramService.get_pictogram(pictogram_id)

        if name is not None:
            pictogram.name = name
        if image_url is not None:
            pictogram.image_url = image_url

        if sound is not None:
            validate_audio_file(sound)
            pictogram.sound = sound

        if generate_image:
            image_bytes = PictogramService._try_generate_image_bytes(pictogram.name)
            if image_bytes:
                pictogram.image.save(
                    f"{pictogram.pk}.png", ContentFile(image_bytes), save=False
                )

        pictogram.save()

        if regenerate_sound and sound is None:
            PictogramService._try_generate_sound(pictogram)

        return pictogram

    @staticmethod
    @transaction.atomic
    def delete_pictogram(*, pictogram_id: int) -> None:
        deleted_count, _ = Pictogram.objects.filter(id=pictogram_id).delete()
        if deleted_count == 0:
            raise ResourceNotFoundError(f"Pictogram {pictogram_id} not found.")
