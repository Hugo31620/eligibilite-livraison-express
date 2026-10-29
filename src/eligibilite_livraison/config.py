"""Configuration par variables d'environnement (un même code, des environnements différents)."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
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
    # Données d'entraînement : jeu synthétique en dev, source ERP MongoDB en test/prod.
    synthetic_rows: int = 6000
    training_min_rows: int = 200
    # Orchestration du réentraînement (ADR-0009).
    retrain_min_new_orders: int = 500
    retrain_interval_minutes: int = 1440
    # repr=False : l'URI peut contenir un mot de passe, elle ne doit jamais finir dans un log.
    mongo_uri: str = field(default="mongodb://localhost:27017", repr=False)
    mongo_database: str = "livraison_express"
    mongo_source_collection: str = "orders"
    mongo_orders_collection: str = "api_orders"

    def __post_init__(self) -> None:
        ensure_valid_model_version(self.model_version)
        if not 0.0 <= self.prediction_threshold <= 1.0:
            raise ConfigurationError("PREDICTION_THRESHOLD doit être compris entre 0 et 1.")
        counts = (
            self.synthetic_rows,
            self.training_min_rows,
            self.retrain_min_new_orders,
            self.retrain_interval_minutes,
        )
        if min(counts) < 1:
            raise ConfigurationError(
                "SYNTHETIC_ROWS, TRAINING_MIN_ROWS, RETRAIN_MIN_NEW_ORDERS et "
                "RETRAIN_INTERVAL_MINUTES doivent être strictement positifs."
            )
        if self.mongo_source_collection == self.mongo_orders_collection:
            raise ConfigurationError(
                "MONGO_ORDERS_COLLECTION doit différer de MONGO_SOURCE_COLLECTION : "
                "l'application n'écrit jamais dans la collection alimentée par l'ERP."
            )

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
            synthetic_rows=_parse_int(environ, "SYNTHETIC_ROWS", defaults.synthetic_rows),
            training_min_rows=_parse_int(environ, "TRAINING_MIN_ROWS", defaults.training_min_rows),
            retrain_min_new_orders=_parse_int(
                environ, "RETRAIN_MIN_NEW_ORDERS", defaults.retrain_min_new_orders
            ),
            retrain_interval_minutes=_parse_int(
                environ, "RETRAIN_INTERVAL_MINUTES", defaults.retrain_interval_minutes
            ),
            mongo_uri=environ.get("MONGO_URI", defaults.mongo_uri),
            mongo_database=environ.get("MONGO_DATABASE", defaults.mongo_database),
            mongo_source_collection=environ.get(
                "MONGO_SOURCE_COLLECTION", defaults.mongo_source_collection
            ),
            mongo_orders_collection=environ.get(
                "MONGO_ORDERS_COLLECTION", defaults.mongo_orders_collection
            ),
        )


def _parse_int(environ: Mapping[str, str], name: str, default: int) -> int:
    value = environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} doit être un nombre entier.") from error


def _parse_bool(value: str | None, default: bool, name: str) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} doit valoir true ou false.")
