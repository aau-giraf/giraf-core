"""Seed the database with sample data for local development."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

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
        self.stdout.write("Seeding development data...\n")

        # ── Users ──────────────────────────────────────────────
        admin = self._create_user("admin", "Admin", "Adminsen", is_superuser=True, is_staff=True)
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
        grade_1a = self._create_grade("1A", sunflower, [emil, freja])
        grade_2b = self._create_grade("2B", sunflower, [oscar])
        grade_3c = self._create_grade("3C", oak, [ida, noah, alma])

        # ── Pictograms ────────────────────────────────────────
        # Global
        self._create_pictogram("Happy", "https://img.giraf.dev/happy.png")
        self._create_pictogram("Sad", "https://img.giraf.dev/sad.png")
        self._create_pictogram("Eat", "https://img.giraf.dev/eat.png")

        # Org-scoped
        self._create_pictogram("School Bus", "https://img.giraf.dev/bus.png", organization=sunflower)
        self._create_pictogram("Lunchroom", "https://img.giraf.dev/lunch.png", organization=sunflower)
        self._create_pictogram("Gymnasium", "https://img.giraf.dev/gym.png", organization=oak)

        # Citizen-scoped
        self._create_pictogram("Emil's Zoo Photo", "https://img.giraf.dev/emil-zoo.png", organization=sunflower, citizen=emil)
        self._create_pictogram("Ida's Cat", "https://img.giraf.dev/ida-cat.png", organization=oak, citizen=ida)

        # ── Invitations ───────────────────────────────────────
        Invitation.objects.get_or_create(
            organization=sunflower,
            sender=anna,
            receiver=mikkel,
            defaults={"status": "pending"},
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

    def _create_pictogram(self, name, image_url, organization=None, citizen=None):
        defaults = {"image_url": image_url}
        if citizen:
            defaults["citizen"] = citizen
        pictogram, created = Pictogram.objects.get_or_create(
            name=name,
            organization=organization,
            defaults=defaults,
        )
        verb = "Created" if created else "Exists"
        scope = "global"
        if citizen:
            scope = f"citizen ({citizen})"
        elif organization:
            scope = f"org ({organization.name})"
        self.stdout.write(f"  {verb} pictogram: {name} [{scope}]")
        return pictogram
