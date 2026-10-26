"""Matrice des droits (ADR-0007) : chaque rôle n'accède qu'à ce qui lui est permis."""

import pytest

from tests.api.conftest import headers_for

# (méthode, chemin, rôle minimal requis ; None = public)
ROUTES = [
    ("get", "/health", None),
    ("get", "/health/ready", None),
    ("get", "/v1/model", "guest"),
    ("post", "/v1/predictions", "user"),
    ("post", "/v1/predictions/batch", "user"),
    ("post", "/v1/orders", "user"),
    ("get", "/v1/orders/CMD-SECURITE", "admin"),
]
LEVEL = {None: -1, "guest": 0, "user": 1, "admin": 2}


def _call(client, method, path, valid_order, headers):
    if path == "/v1/predictions/batch":
        return client.post(path, json={"orders": [valid_order]}, headers=headers)
    if method == "post":
        return client.post(path, json=valid_order, headers=headers)
    return client.get(path, headers=headers)


@pytest.fixture
def seeded_client(anonymous_client, valid_order):
    anonymous_client.post(
        "/v1/orders", json={**valid_order, "order_id": "CMD-SECURITE"}, headers=headers_for("user")
    )
    return anonymous_client


@pytest.mark.parametrize(("method", "path", "required"), ROUTES)
@pytest.mark.parametrize("role", ["guest", "user", "admin"])
def test_role_matrix(seeded_client, valid_order, method, path, required, role):
    response = _call(seeded_client, method, path, valid_order, headers_for(role))

    if LEVEL[role] >= LEVEL[required]:
        assert response.status_code < 400, response.text
    else:
        assert response.status_code == 403
        assert response.json()["error"] == "forbidden"


@pytest.mark.parametrize(("method", "path", "required"), [r for r in ROUTES if r[2]])
@pytest.mark.parametrize(
    "headers",
    [{}, {"X-API-Key": "sk_test_inconnue"}, headers_for("expired")],
    ids=["sans-cle", "cle-inconnue", "cle-expiree"],
)
def test_protected_routes_reject_missing_unknown_or_expired_keys(
    anonymous_client, valid_order, method, path, required, headers
):
    response = _call(anonymous_client, method, path, valid_order, headers)

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    assert response.headers["WWW-Authenticate"].startswith("APIKey")


def test_authentication_happens_before_body_validation(anonymous_client):
    """Un inconnu n'obtient aucune information sur le schéma attendu."""
    response = anonymous_client.post("/v1/predictions", json={"n_importe": "quoi"})
    assert response.status_code == 401


def test_the_key_never_appears_in_responses(anonymous_client):
    response = anonymous_client.get("/v1/model", headers={"X-API-Key": "sk_test_inconnue"})
    assert "sk_test_inconnue" not in response.text


def test_key_rotation_needs_no_restart(anonymous_client, api_keys_file):
    """Révoquer une clé dans le fichier prend effet immédiatement."""
    from eligibilite_livraison.infrastructure.dev.json_file_api_key_store import (
        JsonFileApiKeyStore,
    )

    assert anonymous_client.get("/v1/model", headers=headers_for("guest")).status_code == 200
    JsonFileApiKeyStore(api_keys_file).revoke("guest")
    import os

    stat = api_keys_file.stat()
    os.utime(api_keys_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    assert anonymous_client.get("/v1/model", headers=headers_for("guest")).status_code == 401
