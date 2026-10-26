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
