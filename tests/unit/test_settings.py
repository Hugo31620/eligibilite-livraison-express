from pathlib import Path

import pytest

from eligibilite_livraison.config import Settings
from eligibilite_livraison.domain.errors import ConfigurationError, InvalidModelVersionError


def test_defaults_without_environment():
    settings = Settings.from_env({})
    assert settings.env == "dev"
    assert settings.model_version == "1.0.0"
    assert settings.prediction_threshold == 0.5


def test_environment_overrides_defaults():
    settings = Settings.from_env(
        {
            "APP_ENV": "dev",
            "MODEL_VERSION": "2.1.0",
            "ARTIFACTS_DIR": "/srv/models",
            "ORDERS_DB_PATH": "/srv/orders.db",
            "PREDICTION_THRESHOLD": "0.7",
        }
    )
    assert settings.model_version == "2.1.0"
    assert settings.artifacts_dir == Path("/srv/models")
    assert settings.prediction_threshold == 0.7


@pytest.mark.parametrize("threshold", ["1.5", "-0.1", "abc"])
def test_invalid_threshold_is_rejected(threshold):
    with pytest.raises(ConfigurationError):
        Settings.from_env({"PREDICTION_THRESHOLD": threshold})


@pytest.mark.parametrize("version", ["latest", "1.0", "../1.0.0", ""])
def test_invalid_model_version_is_rejected(version):
    with pytest.raises(InvalidModelVersionError):
        Settings.from_env({"MODEL_VERSION": version})


def test_security_settings():
    settings = Settings.from_env(
        {"API_KEYS_FILE": "/run/secrets/keys.json", "EXPOSE_API_DOCS": "false"}
    )
    assert settings.api_keys_file == Path("/run/secrets/keys.json")
    assert settings.expose_api_docs is False
    assert Settings.from_env({}).expose_api_docs is True


def test_invalid_boolean_is_rejected():
    with pytest.raises(ConfigurationError):
        Settings.from_env({"EXPOSE_API_DOCS": "peut-etre"})


def test_mongo_settings_come_from_the_environment():
    settings = Settings.from_env(
        {
            "APP_ENV": "test",
            "MONGO_URI": "mongodb://user:secret@mongo:27017",
            "MONGO_DATABASE": "analytique",
            "TRAINING_MIN_ROWS": "50",
        }
    )
    assert settings.mongo_database == "analytique"
    assert settings.mongo_source_collection == "orders"
    assert settings.mongo_orders_collection == "api_orders"
    assert settings.training_min_rows == 50


def test_mongo_uri_never_appears_in_the_settings_repr():
    settings = Settings.from_env({"MONGO_URI": "mongodb://user:Mdp-T0p-Confidentiel@mongo:27017"})
    assert "Mdp-T0p-Confidentiel" not in repr(settings)


def test_the_application_can_never_write_into_the_erp_collection():
    with pytest.raises(ConfigurationError, match="MONGO_ORDERS_COLLECTION"):
        Settings.from_env({"MONGO_ORDERS_COLLECTION": "orders"})


@pytest.mark.parametrize(
    "name",
    ["SYNTHETIC_ROWS", "TRAINING_MIN_ROWS", "RETRAIN_MIN_NEW_ORDERS", "RETRAIN_INTERVAL_MINUTES"],
)
@pytest.mark.parametrize("value", ["abc", "0"])
def test_invalid_row_counts_are_rejected(name, value):
    with pytest.raises(ConfigurationError):
        Settings.from_env({name: value})
