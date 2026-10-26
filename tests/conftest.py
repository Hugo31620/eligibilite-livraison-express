from datetime import timedelta

import pytest

from eligibilite_livraison.config import Settings
from eligibilite_livraison.container import build_container
from eligibilite_livraison.data.synthetic import SyntheticDatasetSource
from eligibilite_livraison.domain.security import ApiKeyRecord, Role, hash_api_key, utc_now
from eligibilite_livraison.infrastructure.dev.file_model_repository import FileModelRepository
from eligibilite_livraison.infrastructure.dev.json_file_api_key_store import JsonFileApiKeyStore
from eligibilite_livraison.ml.training import TrainingService

MODEL_VERSION = "1.0.0"

# Clés de test (jamais de vraies clés dans le dépôt) : une par rôle, plus une expirée.
API_KEYS = {
    "guest": "sk_test_guest",
    "user": "sk_test_user",
    "admin": "sk_test_admin",
    "expired": "sk_test_expired",
}

VALID_ORDER = {
    "hour": 14,
    "day_of_week": 2,
    "weekend": 0,
    "distance_km": 3.5,
    "order_value_eur": 89.9,
    "weight_kg": 2.4,
    "stock_available": 1,
    "preparation_time_min": 18,
    "carrier_capacity": 0.85,
    "weather": "normal",
    "delivery_zone": "centre",
    "customer_type": "premium",
}

HARD_ORDER = {
    "hour": 21,
    "day_of_week": 6,
    "weekend": 1,
    "distance_km": 28,
    "order_value_eur": 25.0,
    "weight_kg": 18,
    "stock_available": 0,
    "preparation_time_min": 70,
    "carrier_capacity": 0.25,
    "weather": "orage",
    "delivery_zone": "rurale",
    "customer_type": "standard",
}


@pytest.fixture
def valid_order() -> dict:
    return dict(VALID_ORDER)


@pytest.fixture
def hard_order() -> dict:
    return dict(HARD_ORDER)


@pytest.fixture(scope="session")
def artifacts_dir(tmp_path_factory):
    """Un modèle entraîné une seule fois pour toute la session de tests (jeu réduit)."""
    root = tmp_path_factory.mktemp("artifacts")
    TrainingService(SyntheticDatasetSource(n_rows=1500), FileModelRepository(root)).run(
        MODEL_VERSION
    )
    return root


@pytest.fixture
def api_keys_file(tmp_path):
    path = tmp_path / "api_keys.json"
    store = JsonFileApiKeyStore(path)
    later, earlier = utc_now() + timedelta(days=30), utc_now() - timedelta(days=1)
    for name in ("guest", "user", "admin"):
        store.add(ApiKeyRecord(name, Role(name), hash_api_key(API_KEYS[name]), later))
    store.add(ApiKeyRecord("expired", Role.ADMIN, hash_api_key(API_KEYS["expired"]), earlier))
    return path


@pytest.fixture
def settings(tmp_path, artifacts_dir, api_keys_file) -> Settings:
    return Settings(
        model_version=MODEL_VERSION,
        artifacts_dir=artifacts_dir,
        orders_db_path=tmp_path / "orders.db",
        api_keys_file=api_keys_file,
    )


@pytest.fixture
def container(settings):
    return build_container(settings)
