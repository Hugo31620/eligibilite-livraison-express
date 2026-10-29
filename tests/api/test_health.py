from eligibilite_livraison import __version__


def test_health_is_alive(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "eligibilite-livraison-express",
        "version": __version__,
    }


def test_ready_when_model_and_store_are_available(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"] == {"model": "loaded", "order_store": "reachable"}


def test_not_ready_without_model_but_still_alive(client_without_model):
    ready = client_without_model.get("/health/ready")
    assert ready.status_code == 503
    assert ready.json()["status"] == "not_ready"
    assert ready.json()["checks"]["model"] == "not_loaded"
    assert client_without_model.get("/health").status_code == 200
