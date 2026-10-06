def test_order_is_accepted_and_can_be_read_back(client, valid_order):
    created = client.post("/v1/orders", json={**valid_order, "order_id": "CMD-000042"})

    assert created.status_code == 202
    assert created.json() == {"order_id": "CMD-000042", "status": "accepted"}

    stored = client.get("/v1/orders/CMD-000042")
    assert stored.status_code == 200
    assert stored.json()["distance_km"] == 3.5
    assert stored.json()["weather"] == "normal"


def test_identifier_is_generated_when_absent(client, valid_order):
    created = client.post("/v1/orders", json=valid_order).json()

    assert created["order_id"].startswith("CMD-")
    assert client.get(f"/v1/orders/{created['order_id']}").status_code == 200


def test_unknown_order_returns_404_with_error_body(client):
    response = client.get("/v1/orders/CMD-INCONNUE")
    assert response.status_code == 404
    assert response.json()["error"] == "order_not_found"


def test_duplicate_identifier_is_rejected(client, valid_order):
    payload = {**valid_order, "order_id": "CMD-1"}
    assert client.post("/v1/orders", json=payload).status_code == 202

    response = client.post("/v1/orders", json=payload)

    assert response.status_code == 422
    assert response.json()["error"] == "duplicate_order"


def test_invalid_order_returns_422_with_details(client, valid_order):
    del valid_order["distance_km"]
    response = client.post("/v1/orders", json={**valid_order, "coupon": "X"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert any("distance_km" in detail for detail in body["details"])
    assert any("coupon" in detail for detail in body["details"])


def test_validation_errors_do_not_echo_submitted_values(client, valid_order):
    response = client.post("/v1/orders", json={**valid_order, "weather": "SECRET-VALUE"})
    assert "SECRET-VALUE" not in response.text
