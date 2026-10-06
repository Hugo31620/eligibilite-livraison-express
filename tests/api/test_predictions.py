import pytest


def test_prediction_matches_contract(client, valid_order):
    response = client.post("/v1/predictions", json=valid_order)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "order_id",
        "express_eligible",
        "decision",
        "probability",
        "model_version",
        "predicted_at",
        "latency_ms",
    }
    assert body["decision"] == "oui"
    assert body["express_eligible"] is True
    assert body["model_version"] == "1.0.0"


def test_hard_order_is_not_eligible(client, hard_order):
    body = client.post("/v1/predictions", json=hard_order).json()
    assert body["decision"] == "non"
    assert body["express_eligible"] is False


def test_provided_order_id_is_echoed(client, valid_order):
    body = client.post("/v1/predictions", json={**valid_order, "order_id": "CMD-9"}).json()
    assert body["order_id"] == "CMD-9"


@pytest.mark.parametrize("missing", ["distance_km", "weather"])
def test_missing_feature_returns_422(client, valid_order, missing):
    del valid_order[missing]
    response = client.post("/v1/predictions", json=valid_order)
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_unavailable_model_returns_503(client_without_model, valid_order):
    response = client_without_model.post("/v1/predictions", json=valid_order)
    assert response.status_code == 503
    assert response.json()["error"] == "model_not_found"


def test_prediction_does_not_persist_the_order(client, valid_order):
    client.post("/v1/predictions", json={**valid_order, "order_id": "CMD-77"})
    assert client.get("/v1/orders/CMD-77").status_code == 404
