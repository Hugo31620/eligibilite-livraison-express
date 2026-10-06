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
        )
