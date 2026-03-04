"""Business logic for citizen operations."""

from django.db import transaction
from django.db.models import QuerySet

from apps.citizens.models import Citizen
from core.exceptions import ResourceNotFoundError


class CitizenService:
    @staticmethod
    def _get_citizen_or_raise(citizen_id: int) -> Citizen:
        try:
            return Citizen.objects.select_related("organization").get(id=citizen_id)
        except Citizen.DoesNotExist:
            raise ResourceNotFoundError(f"Citizen {citizen_id} not found.")

    @staticmethod
    @transaction.atomic
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
        return CitizenService._get_citizen_or_raise(citizen_id)

    @staticmethod
    @transaction.atomic
    def update_citizen(*, citizen_id: int, first_name: str | None = None, last_name: str | None = None) -> Citizen:
        citizen = CitizenService._get_citizen_or_raise(citizen_id)
        update_fields: list[str] = []
        if first_name is not None:
            citizen.first_name = first_name
            update_fields.append("first_name")
        if last_name is not None:
            citizen.last_name = last_name
            update_fields.append("last_name")
        if update_fields:
            citizen.save(update_fields=update_fields)
        return citizen

    @staticmethod
    @transaction.atomic
    def delete_citizen(*, citizen_id: int) -> None:
        citizen = CitizenService._get_citizen_or_raise(citizen_id)
        citizen.delete()
