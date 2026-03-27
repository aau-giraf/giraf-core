"""Seed the database with sample data for local development."""

import io

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image

from apps.citizens.models import Citizen
from apps.grades.models import Grade
from apps.invitations.models import Invitation
from apps.organizations.models import Membership, Organization, OrgRole
from apps.pictograms.models import Pictogram

User = get_user_model()

PASSWORD = "devpass123"


class Command(BaseCommand):
    help = "Populate the database with sample data for local development."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stderr.write(
                self.style.ERROR(
                    "ERROR: seed_dev_data can only run with DEBUG=True. "
                    "This command is intended for local development only."
                )
            )
            return

        self.stdout.write("Seeding development data...\n")

        # ── Users ──────────────────────────────────────────────
        self._create_user("admin", "Admin", "Adminsen", is_superuser=True, is_staff=True)
        anna = self._create_user("anna", "Anna", "Pedersen")
        lars = self._create_user("lars", "Lars", "Mortensen")
        sofie = self._create_user("sofie", "Sofie", "Nielsen")
        mikkel = self._create_user("mikkel", "Mikkel", "Jensen")

        # ── Organizations ──────────────────────────────────────
        sunflower, _ = Organization.objects.get_or_create(name="Sunflower School")
        oak, _ = Organization.objects.get_or_create(name="Oak Tree Academy")

        # ── Memberships ────────────────────────────────────────
        self._ensure_membership(anna, sunflower, OrgRole.OWNER)
        self._ensure_membership(sofie, sunflower, OrgRole.MEMBER)
        self._ensure_membership(lars, oak, OrgRole.OWNER)
        self._ensure_membership(mikkel, oak, OrgRole.MEMBER)
        self._ensure_membership(sofie, oak, OrgRole.MEMBER)

        # ── Citizens ──────────────────────────────────────────
        emil = self._create_citizen("Emil", "Andersen", sunflower)
        freja = self._create_citizen("Freja", "Kristensen", sunflower)
        oscar = self._create_citizen("Oscar", "Larsen", sunflower)
        ida = self._create_citizen("Ida", "Rasmussen", oak)
        noah = self._create_citizen("Noah", "Thomsen", oak)
        alma = self._create_citizen("Alma", "Christiansen", oak)

        # ── Grades ─────────────────────────────────────────────
        self._create_grade("1A", sunflower, [emil, freja])
        self._create_grade("2B", sunflower, [oscar])
        self._create_grade("3C", oak, [ida, noah, alma])

        # ── Pictograms ────────────────────────────────────────
        # Global
        self._create_pictogram("Happy", "#FFD700", organization=None)
        self._create_pictogram("Sad", "#4169E1", organization=None)
        self._create_pictogram("Eat", "#32CD32", organization=None)

        # Org-scoped
        self._create_pictogram("School Bus", "#FF8C00", organization=sunflower)
        self._create_pictogram("Lunchroom", "#8B4513", organization=sunflower)
        self._create_pictogram("Gymnasium", "#DC143C", organization=oak)

        # Citizen-scoped
        self._create_pictogram("Emil's Zoo Photo", "#9370DB", organization=sunflower, citizen=emil)
        self._create_pictogram("Ida's Cat", "#FF69B4", organization=oak, citizen=ida)

        # ── Invitations ───────────────────────────────────────
        Invitation.objects.get_or_create(
            organization=sunflower,
            receiver=mikkel,
            defaults={"sender": anna, "status": "pending"},
        )

        # ── Summary ───────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS("\nDone! Development data seeded.\n"))
        self.stdout.write("Login credentials (all passwords: devpass123):\n")
        self.stdout.write(f"  {'Username':<12} {'Role':<20} {'Organizations'}\n")
        self.stdout.write(f"  {'─' * 12} {'─' * 20} {'─' * 30}\n")
        self.stdout.write(f"  {'admin':<12} {'superuser':<20} {'(all)'}\n")
        self.stdout.write(f"  {'anna':<12} {'owner':<20} {'Sunflower School'}\n")
        self.stdout.write(f"  {'lars':<12} {'owner':<20} {'Oak Tree Academy'}\n")
        self.stdout.write(f"  {'sofie':<12} {'member':<20} {'Sunflower School, Oak Tree Academy'}\n")
        self.stdout.write(f"  {'mikkel':<12} {'member':<20} {'Oak Tree Academy'}\n")

    def _create_user(self, username, first_name, last_name, **kwargs):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": f"{username}@giraf.dev",
                **kwargs,
            },
        )
        if created:
            user.set_password(PASSWORD)
            user.save(update_fields=["password"])
            self.stdout.write(f"  Created user: {username}")
        else:
            self.stdout.write(f"  User exists: {username}")
        return user

    def _ensure_membership(self, user, organization, role):
        _, created = Membership.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={"role": role},
        )
        verb = "Added" if created else "Exists"
        self.stdout.write(f"  {verb}: {user.username} → {organization.name} ({role})")

    def _create_citizen(self, first_name, last_name, organization):
        citizen, created = Citizen.objects.get_or_create(
            first_name=first_name,
            last_name=last_name,
            organization=organization,
        )
        verb = "Created" if created else "Exists"
        self.stdout.write(f"  {verb} citizen: {citizen}")
        return citizen

    def _create_grade(self, name, organization, citizens):
        grade, created = Grade.objects.get_or_create(
            name=name,
            organization=organization,
        )
        grade.citizens.set(citizens)
        verb = "Created" if created else "Exists"
        self.stdout.write(f"  {verb} grade: {name} ({len(citizens)} citizens)")
        return grade

    def _create_pictogram(self, name, color, organization=None, citizen=None):
        existing = Pictogram.objects.filter(name=name, organization=organization, citizen=citizen).first()
        if existing:
            scope = self._pictogram_scope_label(organization, citizen)
            self.stdout.write(f"  Exists pictogram: {name} [{scope}]")
            return existing

        image_file = self._make_placeholder_image(color)
        pictogram = Pictogram(
            name=name,
            organization=organization,
            citizen=citizen,
        )
        pictogram.image.save(f"{name.lower().replace(' ', '_')}.png", image_file, save=False)
        pictogram.save()

        scope = self._pictogram_scope_label(organization, citizen)
        self.stdout.write(f"  Created pictogram: {name} [{scope}]")
        return pictogram

    @staticmethod
    def _pictogram_scope_label(organization, citizen):
        if citizen:
            return f"citizen ({citizen})"
        if organization:
            return f"org ({organization.name})"
        return "global"

    @staticmethod
    def _make_placeholder_image(color):
        """Generate a simple colored 200x200 PNG placeholder."""
        hex_color = color.lstrip("#")
        rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        img = Image.new("RGB", (200, 200), rgb)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return ContentFile(buf.getvalue())
