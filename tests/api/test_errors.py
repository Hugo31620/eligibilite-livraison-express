from fastapi.testclient import TestClient

from eligibilite_livraison.api.app import create_app
from tests.api.conftest import headers_for


def test_unexpected_error_is_hidden_behind_a_500(container, valid_order, monkeypatch):
    def boom(_order):
        raise RuntimeError("détail interne confidentiel")

    monkeypatch.setattr(container.orders, "collect", boom)
    client = TestClient(
        create_app(container), raise_server_exceptions=False, headers=headers_for("user")
    )

    response = client.post("/v1/orders", json=valid_order)

    assert response.status_code == 500
    assert response.json() == {"error": "internal_error", "message": "Erreur interne du serveur."}


def test_unknown_route_uses_the_error_format(client):
    response = client.get("/n-importe-quoi")
    assert response.status_code == 404
    assert response.json()["error"] == "http_404"
