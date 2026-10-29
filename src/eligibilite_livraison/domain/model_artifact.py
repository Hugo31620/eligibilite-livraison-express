"""Modèle entraîné et métadonnées qui permettent de l'identifier et de le tracer."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from eligibilite_livraison.domain.errors import InvalidModelVersionError

_VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")


def is_model_version(value: str) -> bool:
    return bool(_VERSION_PATTERN.fullmatch(value))


def version_key(version: str) -> tuple[int, int, int]:
    """Clé de tri numérique : 1.10.0 vient bien après 1.9.0."""
    major, minor, patch = ensure_valid_model_version(version).split(".")
    return int(major), int(minor), int(patch)


def next_minor_version(version: str) -> str:
    """Version suivante pour un réentraînement : même contrat de variables, nouvelles données."""
    major, minor, _ = version_key(version)
    return f"{major}.{minor + 1}.0"


def ensure_valid_model_version(version: str) -> str:
    """Impose un format X.Y.Z : la version sert aussi de nom de dossier (ADR-0002)."""
    if not _VERSION_PATTERN.fullmatch(version):
        raise InvalidModelVersionError(
            f"Version de modèle invalide : {version!r} (format attendu : X.Y.Z)"
        )
    return version


@dataclass(frozen=True)
class ModelMetadata:
    model_version: str
    trained_at: datetime
    sklearn_version: str
    target: str
    features: list[str]
    numeric_features: list[str]
    categorical_features: list[str]
    metrics: dict[str, float]
    training_rows: int
    test_rows: int
    model_sha256: str | None = None  # empreinte de model.joblib, vérifiée avant chargement


@dataclass(frozen=True)
class ModelArtifact:
    pipeline: Any  # sklearn.pipeline.Pipeline : l'API n'a besoin que de predict_proba
    metadata: ModelMetadata
