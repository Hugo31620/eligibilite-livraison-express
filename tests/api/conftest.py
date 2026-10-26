from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from eligibilite_livraison.api.app import create_app
from eligibilite_livraison.container import build_container
from tests.conftest import API_KEYS


def headers_for(role: str) -> dict[str, str]:
    return {"X-API-Key": API_KEYS[role]}


@pytest.fixture
def anonymous_client(container):
    """Client sans clé d'API."""
    with TestClient(create_app(container)) as test_client:
        yield test_client


@pytest.fixture
def client(anonymous_client):
    """Client administrateur : les tests fonctionnels ne testent pas les droits."""
    anonymous_client.headers.update(headers_for("admin"))
    return anonymous_client


@pytest.fixture
def client_without_model(tmp_path, settings):
    """API dont le modèle n'a pas encore été entraîné."""
    empty = replace(settings, artifacts_dir=tmp_path / "empty")
    app = create_app(build_container(empty))
    with TestClient(app, headers=headers_for("admin")) as test_client:
        yield test_client
