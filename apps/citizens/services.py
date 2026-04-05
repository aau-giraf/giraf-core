"""Business logic for citizen operations."""

from django.db.models import QuerySet

from apps.citizens.models import Citizen
from core.exceptions import ResourceNotFoundError


class CitizenService:
    @staticmethod
    def create_citizen(*, org_id: int, first_name: str, last_name: str) -> Citizen:
        return Citizen.objects.create(
            organization_id=org_id,
            first_name=first_name,
            last_name=last_name,
        )

    @staticmethod
    def list_citizens(org_id: int) -> QuerySet[Citizen]:
        return Citizen.objects.filter(organization_id=org_id)

    @staticmethod
    def get_citizen(citizen_id: int) -> Citizen:
        try:
            return Citizen.objects.select_related("organization").get(id=citizen_id)
        except Citizen.DoesNotExist as e:
            raise ResourceNotFoundError(f"Citizen {citizen_id} not found.") from e

    @staticmethod
    def update_citizen(*, citizen_id: int, first_name: str | None = None, last_name: str | None = None) -> Citizen:
        citizen = CitizenService.get_citizen(citizen_id)
        updates = {k: v for k, v in {"first_name": first_name, "last_name": last_name}.items() if v is not None}
        for field, value in updates.items():
            setattr(citizen, field, value)
        if updates:
            citizen.save(update_fields=list(updates))
        return citizen

    @staticmethod
    def delete_citizen(*, citizen_id: int) -> None:
        deleted_count, _ = Citizen.objects.filter(id=citizen_id).delete()
        if deleted_count == 0:
            raise ResourceNotFoundError(f"Citizen {citizen_id} not found.")
