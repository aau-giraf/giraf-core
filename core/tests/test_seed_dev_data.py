"""Tests for the seed_dev_data management command."""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.citizens.models import Citizen
from apps.grades.models import Grade
from apps.invitations.models import Invitation
from apps.organizations.models import Membership, Organization
from apps.pictograms.models import Pictogram

User = get_user_model()


@pytest.mark.django_db
class TestSeedDevData:
    @pytest.fixture(autouse=True)
    def _enable_debug(self, settings):
        settings.DEBUG = True

    def test_refuses_to_run_without_debug(self, settings):
        settings.DEBUG = False
        call_command("seed_dev_data")
        assert User.objects.count() == 0

    def test_creates_expected_records(self):
        call_command("seed_dev_data")

        assert User.objects.count() == 5
        assert Organization.objects.count() == 2
        assert Membership.objects.count() == 5
        assert Citizen.objects.count() == 6
        assert Grade.objects.count() == 3
        assert Pictogram.objects.count() == 8
        assert Invitation.objects.count() == 1

    def test_is_idempotent(self):
        call_command("seed_dev_data")
        call_command("seed_dev_data")

        assert User.objects.count() == 5
        assert Organization.objects.count() == 2
        assert Pictogram.objects.count() == 8

    def test_pictograms_have_images(self):
        call_command("seed_dev_data")

        for pictogram in Pictogram.objects.all():
            assert pictogram.image, f"Pictogram '{pictogram.name}' has no image"

    def test_superuser_created(self):
        call_command("seed_dev_data")

        admin = User.objects.get(username="admin")
        assert admin.is_superuser
        assert admin.is_staff
