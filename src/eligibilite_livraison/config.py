"""Configuration par variables d'environnement (un même code, des environnements différents)."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from eligibilite_livraison.domain.errors import ConfigurationError
from eligibilite_livraison.domain.model_artifact import ensure_valid_model_version


@dataclass(frozen=True)
class Settings:
    env: str = "dev"
    model_version: str = "1.0.0"
    artifacts_dir: Path = Path("artifacts")
    orders_db_path: Path = Path("data/orders.db")
    prediction_threshold: float = 0.5
    api_keys_file: Path = Path("secrets/api_keys.json")
    expose_api_docs: bool = True

    def __post_init__(self) -> None:
        ensure_valid_model_version(self.model_version)
        if not 0.0 <= self.prediction_threshold <= 1.0:
            raise ConfigurationError("PREDICTION_THRESHOLD doit être compris entre 0 et 1.")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        environ = os.environ if environ is None else environ
        defaults = cls()
        try:
            threshold = float(environ.get("PREDICTION_THRESHOLD", defaults.prediction_threshold))
        except ValueError as error:
            raise ConfigurationError("PREDICTION_THRESHOLD doit être un nombre.") from error
        return cls(
            env=environ.get("APP_ENV", defaults.env),
            model_version=environ.get("MODEL_VERSION", defaults.model_version),
            artifacts_dir=Path(environ.get("ARTIFACTS_DIR", defaults.artifacts_dir)),
            orders_db_path=Path(environ.get("ORDERS_DB_PATH", defaults.orders_db_path)),
            prediction_threshold=threshold,
            api_keys_file=Path(environ.get("API_KEYS_FILE", defaults.api_keys_file)),
            expose_api_docs=_parse_bool(
                environ.get("EXPOSE_API_DOCS"), defaults.expose_api_docs, "EXPOSE_API_DOCS"
            ),
        )


def _parse_bool(value: str | None, default: bool, name: str) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} doit valoir true ou false.")
