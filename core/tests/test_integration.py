"""End-to-end integration test exercising the full user journey."""

import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


def _register(client, username, email):
    return client.post(
        "/api/v1/auth/register",
        data={"username": username, "password": "StrongP@ss123!", "email": email},
        content_type="application/json",
    )


def _login(client, username):
    resp = client.post(
        "/api/v1/token/pair",
        data={"username": username, "password": "StrongP@ss123!"},
        content_type="application/json",
    )
    return {"HTTP_AUTHORIZATION": f"Bearer {resp.json()['access']}"}


@pytest.mark.django_db
class TestFullUserJourney:
    def test_complete_workflow(self, client):
        # 1. Register user A and B
        resp_a = _register(client, "alice", "alice@example.com")
        assert resp_a.status_code == 201

        resp_b = _register(client, "bob", "bob@example.com")
        assert resp_b.status_code == 201

        # 2. Login as A → create org (A becomes owner)
        headers_a = _login(client, "alice")

        resp = client.post(
            "/api/v1/organizations",
            data={"name": "Integration School"},
            content_type="application/json",
            **headers_a,
        )
        assert resp.status_code == 201
        org_id = resp.json()["id"]

        # 3. A sends invitation to B's email
        resp = client.post(
            f"/api/v1/organizations/{org_id}/invitations",
            data={"receiver_email": "bob@example.com"},
            content_type="application/json",
            **headers_a,
        )
        assert resp.status_code == 201
        invitation_id = resp.json()["id"]

        # 4. Login as B → list received → accept invitation
        headers_b = _login(client, "bob")

        resp = client.get("/api/v1/invitations/received", **headers_b)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == invitation_id

        resp = client.post(
            f"/api/v1/invitations/{invitation_id}/accept",
            content_type="application/json",
            **headers_b,
        )
        assert resp.status_code == 200

        # B must re-login to get updated org_roles in JWT
        headers_b = _login(client, "bob")

        # 5. B creates citizen in org (member can create citizens)
        resp = client.post(
            f"/api/v1/organizations/{org_id}/citizens",
            data={"first_name": "Charlie", "last_name": "Child"},
            content_type="application/json",
            **headers_b,
        )
        assert resp.status_code == 201
        citizen_id = resp.json()["id"]

        # 6. A creates grade in org (owner/admin can create grades)
        resp = client.post(
            f"/api/v1/organizations/{org_id}/grades",
            data={"name": "Grade 1"},
            content_type="application/json",
            **headers_a,
        )
        assert resp.status_code == 201
        grade_id = resp.json()["id"]

        # 7. A assigns citizen to grade
        resp = client.post(
            f"/api/v1/grades/{grade_id}/citizens",
            data={"citizen_ids": [citizen_id]},
            content_type="application/json",
            **headers_a,
        )
        assert resp.status_code == 200

        # 8. A creates pictogram in org
        resp = client.post(
            "/api/v1/pictograms",
            data={
                "name": "Happy Face",
                "image_url": "https://example.com/happy.png",
                "organization_id": org_id,
            },
            content_type="application/json",
            **headers_a,
        )
        assert resp.status_code == 201

        # 9. Verify pictogram appears in listing
        resp = client.get(
            f"/api/v1/pictograms?organization_id={org_id}",
            **headers_a,
        )
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()["items"]]
        assert "Happy Face" in names
