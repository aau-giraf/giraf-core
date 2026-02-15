"""Business logic for citizen operations."""

from apps.citizens.models import Citizen


class CitizenService:
    @staticmethod
    def create_citizen(*, org_id: int, first_name: str, last_name: str) -> Citizen:
        return Citizen.objects.create(
            organization_id=org_id,
            first_name=first_name,
            last_name=last_name,
        )

    @staticmethod
    def list_citizens(org_id: int):
        return Citizen.objects.filter(organization_id=org_id)

    @staticmethod
    def get_citizen(citizen_id: int) -> Citizen:
        return Citizen.objects.select_related("organization").get(id=citizen_id)

    @staticmethod
    def update_citizen(citizen: Citizen, **fields) -> Citizen:
        for key, value in fields.items():
            if value is not None:
                setattr(citizen, key, value)
        citizen.save()
        return citizen

    @staticmethod
    def delete_citizen(citizen: Citizen) -> None:
        citizen.delete()
