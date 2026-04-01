"""Tests for Pictogram API endpoints."""

import pytest

from apps.pictograms.tests.utils import make_test_audio, make_test_image
from apps.users.tests.factories import UserFactory
from conftest import auth_header_for_user


@pytest.mark.django_db
class TestPictogramAPI:
    def test_create_pictogram_for_org(self, client, org, owner):
        headers = auth_header_for_user(owner)
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
        headers = auth_header_for_user(owner)
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
        headers = auth_header_for_user(owner)
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

        headers = auth_header_for_user(member)
        response = client.get(f"/api/v1/pictograms?organization_id={org.id}", **headers)
        assert response.status_code == 200
        names = [p["name"] for p in response.json()["items"]]
        assert "Global" in names
        assert "Org Specific" in names

    def test_list_pictograms_search_filters_results(self, client, org, member):
        from apps.pictograms.models import Pictogram

        Pictogram.objects.create(name="Cat", image_url="https://c.com/c.png", organization=org)
        Pictogram.objects.create(name="Dog", image_url="https://d.com/d.png", organization=org)
        Pictogram.objects.create(name="Caterpillar", image_url="https://cp.com/cp.png", organization=org)

        headers = auth_header_for_user(member)
        response = client.get(f"/api/v1/pictograms?organization_id={org.id}&search=cat", **headers)
        assert response.status_code == 200
        names = [p["name"] for p in response.json()["items"]]
        assert "Cat" in names
        assert "Caterpillar" in names
        assert "Dog" not in names

    def test_list_pictograms_empty_search_returns_all(self, client, org, member):
        from apps.pictograms.models import Pictogram

        Pictogram.objects.create(name="Cat", image_url="https://c.com/c.png", organization=org)
        Pictogram.objects.create(name="Dog", image_url="https://d.com/d.png", organization=org)

        headers = auth_header_for_user(member)
        response = client.get(f"/api/v1/pictograms?organization_id={org.id}&search=", **headers)
        assert response.status_code == 200
        names = [p["name"] for p in response.json()["items"]]
        assert "Cat" in names
        assert "Dog" in names

    def test_get_pictogram(self, client, org, member):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="Happy", image_url="https://h.com/h.png", organization=org)

        headers = auth_header_for_user(member)
        response = client.get(f"/api/v1/pictograms/{p.id}", **headers)
        assert response.status_code == 200
        assert "sound_url" in response.json()

    def test_get_global_pictogram_no_org_check(self, client, non_member):
        """Global pictograms (org=None) are accessible to any authenticated user."""
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="Global", image_url="https://g.com/g.png")
        headers = auth_header_for_user(non_member)
        response = client.get(f"/api/v1/pictograms/{p.id}", **headers)
        assert response.status_code == 200

    def test_get_org_pictogram_denied_for_non_member(self, client, org, non_member):
        """Org-scoped pictograms require membership."""
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="Private", image_url="https://p.com/p.png", organization=org)
        headers = auth_header_for_user(non_member)
        response = client.get(f"/api/v1/pictograms/{p.id}", **headers)
        assert response.status_code == 403

    def test_create_api_rejects_no_image_source(self, client, owner, org):
        headers = auth_header_for_user(owner)
        response = client.post(
            "/api/v1/pictograms",
            data={"name": "No Image", "image_url": "", "organization_id": org.id, "generate_sound": False},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 422

    def test_delete_pictogram(self, client, org, owner):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="Happy", image_url="https://h.com/h.png", organization=org)

        headers = auth_header_for_user(owner)
        response = client.delete(f"/api/v1/pictograms/{p.id}", **headers)
        assert response.status_code == 204
        assert not Pictogram.objects.filter(id=p.id).exists()


@pytest.mark.django_db
class TestPictogramPatch:
    def test_patch_name(self, client, org, owner):
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="Old", image_url="https://example.com/pic.png", organization=org)
        headers = auth_header_for_user(owner)
        response = client.patch(
            f"/api/v1/pictograms/{p.id}",
            data={"name": "New"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New"

    def test_patch_nonexistent_returns_404(self, client, org, owner):
        headers = auth_header_for_user(owner)
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
        headers = auth_header_for_user(owner)
        image = make_test_image()
        sound = make_test_audio()
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
        headers = auth_header_for_user(owner)
        sound = make_test_audio()
        response = client.post(
            f"/api/v1/pictograms/{p.id}/sound",
            data={"sound": sound},
            **headers,
        )
        assert response.status_code == 200
        assert response.json()["sound_url"] != ""

    def test_member_can_upload_pictogram(self, client, org, member):
        headers = auth_header_for_user(member)
        image = make_test_image()
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
        headers = auth_header_for_user(member)
        sound = make_test_audio()
        response = client.post(
            f"/api/v1/pictograms/{p.id}/sound",
            data={"sound": sound},
            **headers,
        )
        assert response.status_code == 200
        assert response.json()["sound_url"] != ""


@pytest.mark.django_db
class TestPictogramUpload:
    def test_upload_pictogram_creates_with_image(self, client, org, owner):
        headers = auth_header_for_user(owner)
        image = make_test_image()
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
        headers = auth_header_for_user(owner)
        image = make_test_image()
        response = client.post(
            "/api/v1/pictograms/upload",
            data={"name": "Global Upload", "image": image, "generate_sound": False},
            **headers,
        )
        assert response.status_code == 201
        assert response.json()["organization_id"] is None

    def test_non_superuser_cannot_upload_global_pictogram(self, client, owner):
        headers = auth_header_for_user(owner)
        image = make_test_image()
        response = client.post(
            "/api/v1/pictograms/upload",
            data={"name": "Global Upload", "image": image, "generate_sound": False},
            **headers,
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestPictogramPermissions:
    def test_member_can_create_org_pictogram(self, client, org, member):
        headers = auth_header_for_user(member)
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
        headers = auth_header_for_user(member)
        response = client.delete(f"/api/v1/pictograms/{p.id}", **headers)
        assert response.status_code == 204
        assert not Pictogram.objects.filter(id=p.id).exists()

    def test_non_member_cannot_create_pictogram_in_other_org(self, client, org, non_member):
        headers = auth_header_for_user(non_member)
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
        from apps.pictograms.models import Pictogram

        p = Pictogram.objects.create(name="Global", image_url="https://example.com/g.png", organization=None)
        headers = auth_header_for_user(owner)
        response = client.delete(f"/api/v1/pictograms/{p.id}", **headers)
        assert response.status_code == 403
        assert Pictogram.objects.filter(id=p.id).exists()

    def test_superuser_can_delete_global_pictogram(self, client, db):
        from apps.pictograms.models import Pictogram

        superadmin = UserFactory(username="superadmin", password="testpass123", is_superuser=True)
        p = Pictogram.objects.create(name="Global", image_url="https://example.com/g.png", organization=None)
        headers = auth_header_for_user(superadmin)
        response = client.delete(f"/api/v1/pictograms/{p.id}", **headers)
        assert response.status_code == 204
        assert not Pictogram.objects.filter(id=p.id).exists()


@pytest.mark.django_db
class TestPictogramCitizenScopeAPI:
    def test_member_can_create_citizen_scoped_pictogram(self, client, org, member, citizen):
        headers = auth_header_for_user(member)
        response = client.post(
            "/api/v1/pictograms",
            data={
                "name": "Alice Zoo",
                "image_url": "https://example.com/zoo.png",
                "organization_id": org.id,
                "citizen_id": citizen.id,
                "generate_sound": False,
            },
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 201
        assert response.json()["citizen_id"] == citizen.id
        assert response.json()["organization_id"] == org.id

    def test_non_member_cannot_create_citizen_scoped(self, client, org, non_member, citizen):
        headers = auth_header_for_user(non_member)
        response = client.post(
            "/api/v1/pictograms",
            data={
                "name": "Bad",
                "image_url": "https://example.com/pic.png",
                "organization_id": org.id,
                "citizen_id": citizen.id,
                "generate_sound": False,
            },
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403

    def test_list_for_citizen_returns_hierarchy(self, client, org, member, citizen):
        from apps.pictograms.models import Pictogram

        Pictogram.objects.create(name="Global", image_url="https://g.com/g.png", organization=None)
        Pictogram.objects.create(name="Org", image_url="https://o.com/o.png", organization=org)
        Pictogram.objects.create(
            name="Citizen", image_url="https://c.com/c.png", organization=org, citizen=citizen
        )

        headers = auth_header_for_user(member)
        response = client.get(f"/api/v1/pictograms?citizen_id={citizen.id}", **headers)
        assert response.status_code == 200
        names = [p["name"] for p in response.json()["items"]]
        assert "Global" in names
        assert "Org" in names
        assert "Citizen" in names

    def test_list_for_citizen_excludes_other_citizens(self, client, org, member, citizen):
        from apps.citizens.models import Citizen
        from apps.pictograms.models import Pictogram

        bob = Citizen.objects.create(first_name="Bob", last_name="Test", organization=org)
        Pictogram.objects.create(
            name="Alice Pic", image_url="https://a.com/a.png", organization=org, citizen=citizen
        )
        Pictogram.objects.create(
            name="Bob Pic", image_url="https://b.com/b.png", organization=org, citizen=bob
        )

        headers = auth_header_for_user(member)
        response = client.get(f"/api/v1/pictograms?citizen_id={citizen.id}", **headers)
        assert response.status_code == 200
        names = [p["name"] for p in response.json()["items"]]
        assert "Alice Pic" in names
        assert "Bob Pic" not in names

    def test_upload_citizen_scoped_pictogram(self, client, org, member, citizen):
        from apps.pictograms.tests.utils import make_test_image

        headers = auth_header_for_user(member)
        image = make_test_image()
        response = client.post(
            "/api/v1/pictograms/upload",
            data={
                "name": "Uploaded",
                "image": image,
                "organization_id": org.id,
                "citizen_id": citizen.id,
                "generate_sound": False,
            },
            **headers,
        )
        assert response.status_code == 201
        assert response.json()["citizen_id"] == citizen.id

    def test_non_member_cannot_list_citizen_pictograms(self, client, org, non_member, citizen):
        headers = auth_header_for_user(non_member)
        response = client.get(f"/api/v1/pictograms?citizen_id={citizen.id}", **headers)
        assert response.status_code == 403
