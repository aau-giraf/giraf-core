"""Pictogram model.

Pictograms are visual aids used for communication with autistic children.
They can be global (organization=None), org-scoped, or citizen-scoped.
"""

from django.core.exceptions import ValidationError
from django.db import models


class Pictogram(models.Model):
    """A visual aid image used across GIRAF apps."""

    name = models.CharField(max_length=255)
    image_url = models.CharField(max_length=500, blank=True, default="")
    image = models.ImageField(
        upload_to="pictograms/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    sound = models.FileField(
        upload_to="pictograms/sounds/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="pictograms",
        null=True,
        blank=True,
    )
    citizen = models.ForeignKey(
        "citizens.Citizen",
        on_delete=models.CASCADE,
        related_name="pictograms",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pictograms"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def effective_image_url(self) -> str:
        """Return uploaded image URL if available, otherwise the stored image_url."""
        if self.image:
            return str(self.image.url)
        return self.image_url

    @property
    def effective_sound_url(self) -> str:
        """Return uploaded sound URL if available, otherwise empty string."""
        if self.sound:
            return str(self.sound.url)
        return ""

    def clean(self):
        if not self.image_url and not self.image:
            raise ValidationError("A pictogram must have either an image_url or an uploaded image.")
        if self.citizen_id and not self.organization_id:
            raise ValidationError("A citizen-scoped pictogram must also have an organization.")
        if self.citizen_id and self.organization_id:
            from apps.citizens.models import Citizen

            try:
                citizen = Citizen.objects.get(pk=self.citizen_id)
            except Citizen.DoesNotExist:
                raise ValidationError("Citizen does not exist.")
            if citizen.organization_id != self.organization_id:
                raise ValidationError("Citizen must belong to the pictogram's organization.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
