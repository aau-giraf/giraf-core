"""Grade model.

Grades are class groupings of citizens within an organization.
"""

from django.db import models


class Grade(models.Model):
    """A class/group of citizens within an organization."""

    name = models.CharField(max_length=255)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="grades",
    )
    citizens = models.ManyToManyField(
        "citizens.Citizen",
        related_name="grades",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "grades"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
