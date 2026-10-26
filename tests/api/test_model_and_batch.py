from dataclasses import replace

from fastapi.testclient import TestClient

from eligibilite_livraison.api.app import create_app
from eligibilite_livraison.container import build_container


def test_model_card_describes_the_served_model(client):
    response = client.get("/v1/model")

    assert response.status_code == 200
    card = response.json()
    assert card["project"] == "eligibilite-livraison-express"
    assert card["model_version"] == "1.0.0"
    assert card["target"] == "express_eligible"
    assert card["threshold"] == 0.5
    assert len(card["features"]) == 12
    assert set(card["metrics"]) == {"accuracy", "precision", "recall", "f1_score", "roc_auc"}
    assert card["limitations"]


def test_model_card_without_model_returns_503(client_without_model):
    assert client_without_model.get("/v1/model").status_code == 503


def test_batch_keeps_the_order_of_the_request(client, valid_order, hard_order):
    response = client.post(
        "/v1/predictions/batch",
        json={
            "orders": [
                {**valid_order, "order_id": "A"},
                {**hard_order, "order_id": "B"},
                {**valid_order, "order_id": "C"},
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert [p["order_id"] for p in body["predictions"]] == ["A", "B", "C"]
    assert [p["decision"] for p in body["predictions"]] == ["oui", "non", "oui"]


def test_batch_matches_unit_predictions(client, valid_order, hard_order):
    batch = client.post("/v1/predictions/batch", json={"orders": [valid_order, hard_order]}).json()
    single = [client.post("/v1/predictions", json=o).json() for o in (valid_order, hard_order)]

    assert [p["probability"] for p in batch["predictions"]] == [p["probability"] for p in single]


def test_empty_or_oversized_batch_is_rejected(client, valid_order):
    assert client.post("/v1/predictions/batch", json={"orders": []}).status_code == 422
    too_many = {"orders": [valid_order] * 1001}
    assert client.post("/v1/predictions/batch", json=too_many).status_code == 422


def test_one_invalid_order_rejects_the_whole_batch(client, valid_order):
    invalid = {**valid_order, "hour": 99}
    response = client.post("/v1/predictions/batch", json={"orders": [valid_order, invalid]})
    assert response.status_code == 422
    assert any("orders.1.hour" in detail for detail in response.json()["details"])


def test_docs_can_be_disabled_for_production(settings):
    app = create_app(build_container(replace(settings, expose_api_docs=False)))
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_docs_are_available_in_development(anonymous_client):
    assert anonymous_client.get("/openapi.json").status_code == 200
