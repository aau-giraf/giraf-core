"""Tests for Pictogram model and API endpoints.

Pictograms are visual aids used across all GIRAF apps.
They can be org-specific or global (null organization).
Written BEFORE implementation.
"""

import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.organizations.models import Organization
from apps.users.tests.factories import UserFactory
from conftest import auth_header


def _make_test_image() -> SimpleUploadedFile:
    """Create a minimal valid image file for testing."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile("test.png", buf.read(), content_type="image/png")


def _make_test_audio(name="test.mp3", size=1024) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"\xff" * size, content_type="audio/mpeg")


@pytest.mark.django_db
class TestPictogramModel:
    def test_create_org_pictogram(self):
        from apps.pictograms.models import Pictogram

        org = Organization.objects.create(name="Test School")
        p = Pictogram.objects.create(
            name="Happy Face",
            image_url="https://example.com/happy.png",
            organization=org,
        )
        assert p.pk is not None
        assert p.organization == org
        assert str(p) == "Happy Face"

    def test_create_global_pictogram(self):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(
            name="Sad Face",
            image_url="https://example.com/sad.png",
            organization=None,
        )
        assert p.pk is not None
        assert p.organization is None

    def test_effective_sound_url_empty_when_no_sound(self):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="NoSound", image_url="https://example.com/pic.png")
        assert p.effective_sound_url == ""

    def test_effective_sound_url_returns_file_url(self):
        from apps.pictograms.models import Pictogram

        sound = _make_test_audio()
        p = Pictogram.objects.create(name="WithSound", image_url="https://example.com/pic.png", sound=sound)
        assert p.effective_sound_url != ""
        assert "mp3" in p.effective_sound_url

    def test_clean_still_requires_image(self):
        from apps.pictograms.models import Pictogram

        with pytest.raises(ValidationError):
            Pictogram.objects.create(name="No Image", sound=_make_test_audio())


@pytest.mark.django_db
class TestPictogramAPI:
    def test_create_pictogram_for_org(self, client, org, owner):
        headers = auth_header(client, "owner")
        response = client.post(
            "/api/v1/pictograms",
            data={
                "name": "Happy Face",
                "image_url": "https://example.com/happy.png",
                "organization_id": org.id,
                "generate_sound": False,
            },
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Happy Face"

    def test_create_response_includes_sound_url(self, client, org, owner):
        headers = auth_header(client, "owner")
        response = client.post(
            "/api/v1/pictograms",
            data={
                "name": "Test",
                "image_url": "https://example.com/pic.png",
                "organization_id": org.id,
                "generate_sound": False,
            },
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "sound_url" in data
        assert data["sound_url"] == ""

    def test_create_with_just_image_url_backward_compat(self, client, org, owner):
        """Creating with just image_url still works (generate_sound defaults True but AI is unavailable)."""
        headers = auth_header(client, "owner")
        response = client.post(
            "/api/v1/pictograms",
            data={
                "name": "Compat",
                "image_url": "https://example.com/pic.png",
                "organization_id": org.id,
            },
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Compat"

    def test_list_pictograms_includes_global_and_org(self, client, org, member):
        from apps.pictograms.models import Pictogram

        Pictogram.objects.create(name="Global", image_url="https://g.com/g.png", organization=None)
        Pictogram.objects.create(name="Org Specific", image_url="https://o.com/o.png", organization=org)

        headers = auth_header(client, "member")
        response = client.get(f"/api/v1/pictograms?organization_id={org.id}", **headers)
        assert response.status_code == 200
        names = [p["name"] for p in response.json()["items"]]
        assert "Global" in names
        assert "Org Specific" in names

    def test_get_pictogram(self, client, org, member):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="Happy", image_url="https://h.com/h.png", organization=org)

        headers = auth_header(client, "member")
        response = client.get(f"/api/v1/pictograms/{p.id}", **headers)
        assert response.status_code == 200
        assert "sound_url" in response.json()

    def test_delete_pictogram(self, client, org, owner):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="Happy", image_url="https://h.com/h.png", organization=org)

        headers = auth_header(client, "owner")
        response = client.delete(f"/api/v1/pictograms/{p.id}", **headers)
        assert response.status_code == 204
        assert not Pictogram.objects.filter(id=p.id).exists()


@pytest.mark.django_db
class TestPictogramPatch:
    def test_patch_name(self, client, org, owner):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="Old", image_url="https://example.com/pic.png", organization=org)
        headers = auth_header(client, "owner")
        response = client.patch(
            f"/api/v1/pictograms/{p.id}",
            data={"name": "New"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New"

    def test_patch_nonexistent_returns_404(self, client, org, owner):
        headers = auth_header(client, "owner")
        response = client.patch(
            "/api/v1/pictograms/99999",
            data={"name": "Nope"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestPictogramSoundUpload:
    def test_upload_pictogram_with_sound(self, client, org, owner):
        headers = auth_header(client, "owner")
        image = _make_test_image()
        sound = _make_test_audio()
        response = client.post(
            "/api/v1/pictograms/upload",
            data={
                "name": "WithSound",
                "image": image,
                "sound": sound,
                "organization_id": org.id,
                "generate_sound": False,
            },
            **headers,
        )
        assert response.status_code == 201
        assert response.json()["sound_url"] != ""

    def test_upload_sound_to_existing_pictogram(self, client, org, owner):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="NoSound", image_url="https://example.com/pic.png", organization=org)
        headers = auth_header(client, "owner")
        sound = _make_test_audio()
        response = client.post(
            f"/api/v1/pictograms/{p.id}/sound",
            data={"sound": sound},
            **headers,
        )
        assert response.status_code == 200
        assert response.json()["sound_url"] != ""

    def test_member_can_upload_pictogram(self, client, org, member):
        headers = auth_header(client, "member")
        image = _make_test_image()
        response = client.post(
            "/api/v1/pictograms/upload",
            data={"name": "MemberUpload", "image": image, "organization_id": org.id, "generate_sound": False},
            **headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "MemberUpload"

    def test_member_can_upload_sound(self, client, org, member):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="NeedsSound", image_url="https://example.com/pic.png", organization=org)
        headers = auth_header(client, "member")
        sound = _make_test_audio()
        response = client.post(
            f"/api/v1/pictograms/{p.id}/sound",
            data={"sound": sound},
            **headers,
        )
        assert response.status_code == 200
        assert response.json()["sound_url"] != ""


@pytest.mark.django_db
class TestPictogramValidation:
    def test_pictogram_requires_image_source(self):
        from apps.pictograms.models import Pictogram

        with pytest.raises(ValidationError):
            Pictogram.objects.create(name="No Image", image_url="", image=None)

    def test_pictogram_with_url_only_valid(self):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="URL Only", image_url="https://example.com/pic.png")
        assert p.pk is not None

    def test_pictogram_with_file_only_valid(self):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="File Only", image=_make_test_image())
        assert p.pk is not None

    def test_create_api_rejects_no_image_source(self, client, owner, org):
        headers = auth_header(client, "owner")
        response = client.post(
            "/api/v1/pictograms",
            data={"name": "No Image", "image_url": "", "organization_id": org.id, "generate_sound": False},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 422


@pytest.mark.django_db
class TestPictogramUpload:
    def test_upload_pictogram_creates_with_image(self, client, org, owner):
        headers = auth_header(client, "owner")
        image = _make_test_image()
        response = client.post(
            "/api/v1/pictograms/upload",
            data={"name": "Uploaded", "image": image, "organization_id": org.id, "generate_sound": False},
            **headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Uploaded"

    def test_upload_pictogram_global(self, client, owner):
        owner.is_superuser = True
        owner.save(update_fields=["is_superuser"])
        headers = auth_header(client, "owner")
        image = _make_test_image()
        response = client.post(
            "/api/v1/pictograms/upload",
            data={"name": "Global Upload", "image": image, "generate_sound": False},
            **headers,
        )
        assert response.status_code == 201
        assert response.json()["organization_id"] is None

    def test_non_superuser_cannot_upload_global_pictogram(self, client, owner):
        headers = auth_header(client, "owner")
        image = _make_test_image()
        response = client.post(
            "/api/v1/pictograms/upload",
            data={"name": "Global Upload", "image": image, "generate_sound": False},
            **headers,
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestPictogramPermissions:
    def test_member_can_create_org_pictogram(self, client, org, member):
        headers = auth_header(client, "member")
        response = client.post(
            "/api/v1/pictograms",
            data={
                "name": "Member Created",
                "image_url": "https://example.com/pic.png",
                "organization_id": org.id,
                "generate_sound": False,
            },
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 201

    def test_member_can_delete_org_pictogram(self, client, org, member):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="OrgPic", image_url="https://example.com/p.png", organization=org)
        headers = auth_header(client, "member")
        response = client.delete(f"/api/v1/pictograms/{p.id}", **headers)
        assert response.status_code == 204
        assert not Pictogram.objects.filter(id=p.id).exists()

    def test_non_member_cannot_create_pictogram_in_other_org(self, client, org, non_member):
        headers = auth_header(client, "outsider")
        response = client.post(
            "/api/v1/pictograms",
            data={
                "name": "Cross Org",
                "image_url": "https://example.com/pic.png",
                "organization_id": org.id,
            },
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403

    def test_non_superuser_cannot_delete_global_pictogram(self, client, owner):
        """P0 fix: non-superuser must not be able to delete global pictograms."""
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="Global", image_url="https://example.com/g.png", organization=None)
        headers = auth_header(client, "owner")
        response = client.delete(f"/api/v1/pictograms/{p.id}", **headers)
        assert response.status_code == 403
        assert Pictogram.objects.filter(id=p.id).exists()

    def test_superuser_can_delete_global_pictogram(self, client, db):
        """P0 fix: superuser can delete global pictograms."""
        from apps.pictograms.models import Pictogram

        UserFactory(username="superadmin", password="testpass123", is_superuser=True)
        p = Pictogram.objects.create(name="Global", image_url="https://example.com/g.png", organization=None)
        headers = auth_header(client, "superadmin")
        response = client.delete(f"/api/v1/pictograms/{p.id}", **headers)
        assert response.status_code == 204
        assert not Pictogram.objects.filter(id=p.id).exists()
