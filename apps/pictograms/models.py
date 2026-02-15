"""Pictogram model.

Pictograms are visual aids used for communication with autistic children.
They can belong to an organization (custom) or be global (organization=None).
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
    organization = models.ForeignKey(
        "organizations.Organization",
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

    def clean(self):
        if not self.image_url and not self.image:
            raise ValidationError("A pictogram must have either an image_url or an uploaded image.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
