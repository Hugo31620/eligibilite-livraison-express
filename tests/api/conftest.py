import pytest
from fastapi.testclient import TestClient

from eligibilite_livraison.api.app import create_app


@pytest.fixture
def client(container):
    with TestClient(create_app(container)) as test_client:
        yield test_client


@pytest.fixture
def client_without_model(tmp_path, settings):
    """API dont le modèle n'a pas encore été entraîné."""
    from dataclasses import replace

    from eligibilite_livraison.container import build_container

    empty = replace(settings, artifacts_dir=tmp_path / "empty")
    with TestClient(create_app(build_container(empty))) as test_client:
        yield test_client
