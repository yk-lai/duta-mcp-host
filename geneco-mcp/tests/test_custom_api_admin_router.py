from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import TEST_ADMIN_API_KEY

CREDENTIALS_BODY = {
    "base_url": "https://custom-api.geneco.example",
    "username": "cxchat-svc",
    "password": "super-secret-value",
}


def test_upsert_requires_admin_key(client: TestClient) -> None:
    resp = client.post("/geneco/custom-api-credentials", json=CREDENTIALS_BODY)
    assert resp.status_code == 401


def test_upsert_rejects_wrong_admin_key(client: TestClient) -> None:
    resp = client.post(
        "/geneco/custom-api-credentials",
        headers={"X-Admin-Api-Key": "wrong-key"},
        json=CREDENTIALS_BODY,
    )
    assert resp.status_code == 401


def test_upsert_then_get_never_exposes_the_real_secret(client: TestClient) -> None:
    resp = client.post(
        "/geneco/custom-api-credentials",
        headers={"X-Admin-Api-Key": TEST_ADMIN_API_KEY},
        json=CREDENTIALS_BODY,
    )
    assert resp.status_code == 200
    assert resp.json()["password"] == "•••"
    assert "super-secret-value" not in resp.text

    get_resp = client.get(
        "/geneco/custom-api-credentials", headers={"X-Admin-Api-Key": TEST_ADMIN_API_KEY}
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["password"] == "•••"
    assert "super-secret-value" not in get_resp.text


def test_get_missing_tenant_is_404(client: TestClient) -> None:
    resp = client.get(
        "/unknown-tenant/custom-api-credentials", headers={"X-Admin-Api-Key": TEST_ADMIN_API_KEY}
    )
    assert resp.status_code == 404


def test_delete_then_get_is_404(client: TestClient) -> None:
    client.post(
        "/geneco/custom-api-credentials",
        headers={"X-Admin-Api-Key": TEST_ADMIN_API_KEY},
        json=CREDENTIALS_BODY,
    )
    del_resp = client.delete(
        "/geneco/custom-api-credentials", headers={"X-Admin-Api-Key": TEST_ADMIN_API_KEY}
    )
    assert del_resp.status_code == 204
    get_resp = client.get(
        "/geneco/custom-api-credentials", headers={"X-Admin-Api-Key": TEST_ADMIN_API_KEY}
    )
    assert get_resp.status_code == 404


def test_delete_missing_tenant_is_404(client: TestClient) -> None:
    resp = client.delete(
        "/unknown-tenant/custom-api-credentials", headers={"X-Admin-Api-Key": TEST_ADMIN_API_KEY}
    )
    assert resp.status_code == 404


def test_d365_and_custom_api_credentials_are_independent(client: TestClient) -> None:
    d365_body = {
        "org_url": "https://geneco.crm.dynamics.com",
        "tenant_id": "77dee05b-8ff2-4aee-81a7-461ed9ab3456",
        "client_id": "77fa3ab9-8247-48e4-8ad5-5fc959ef7f24",
        "client_secret": "d365-secret",
    }
    client.post(
        "/geneco/credentials", headers={"X-Admin-Api-Key": TEST_ADMIN_API_KEY}, json=d365_body
    )
    client.post(
        "/geneco/custom-api-credentials",
        headers={"X-Admin-Api-Key": TEST_ADMIN_API_KEY},
        json=CREDENTIALS_BODY,
    )

    del_resp = client.delete(
        "/geneco/custom-api-credentials", headers={"X-Admin-Api-Key": TEST_ADMIN_API_KEY}
    )
    assert del_resp.status_code == 204

    d365_get = client.get("/geneco/credentials", headers={"X-Admin-Api-Key": TEST_ADMIN_API_KEY})
    assert d365_get.status_code == 200
