"""Artefacts de modèle dans un répertoire local versionné (ADR-0002, option A).

Disposition : ``<racine>/<version>/model.joblib`` + ``<racine>/<version>/metadata.json``.
Une version publiée est immuable.
"""

import json
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import joblib

from eligibilite_livraison.abstractions.model_repository import ModelRepository
from eligibilite_livraison.domain.errors import (
    ModelAlreadyExistsError,
    ModelNotFoundError,
    ModelUnavailableError,
)
from eligibilite_livraison.domain.model_artifact import (
    ModelArtifact,
    ModelMetadata,
    ensure_valid_model_version,
)

MODEL_FILENAME = "model.joblib"
METADATA_FILENAME = "metadata.json"


class FileModelRepository(ModelRepository):
    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def save(self, artifact: ModelArtifact) -> None:
        version = artifact.metadata.model_version
        target = self._version_dir(version)
        if target.exists():
            raise ModelAlreadyExistsError(
                f"La version {version} existe déjà dans {self._root}. "
                "Une version publiée est immuable : choisissez un nouveau numéro de version."
            )

        # Écriture dans un dossier temporaire puis renommage : jamais d'artefact à moitié écrit.
        staging = self._root / f".{version}.tmp"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True)
        try:
            joblib.dump(artifact.pipeline, staging / MODEL_FILENAME)
            (staging / METADATA_FILENAME).write_text(
                json.dumps(_metadata_to_dict(artifact.metadata), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            staging.rename(target)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def load(self, version: str) -> ModelArtifact:
        directory = self._version_dir(version)
        model_path = directory / MODEL_FILENAME
        metadata_path = directory / METADATA_FILENAME
        if not (model_path.is_file() and metadata_path.is_file()):
            raise ModelNotFoundError(
                f"Modèle {version} introuvable dans {self._root}. "
                "Lancez l'entraînement : express-train"
            )
        try:
            metadata = _metadata_from_dict(json.loads(metadata_path.read_text(encoding="utf-8")))
            pipeline = joblib.load(model_path)
        except Exception as error:  # noqa: BLE001 - un pickle corrompu peut lever n'importe quoi
            raise ModelUnavailableError(
                f"Artefact du modèle {version} illisible : {error}"
            ) from error
        return ModelArtifact(pipeline=pipeline, metadata=metadata)

    def _version_dir(self, version: str) -> Path:
        # La version devient un nom de dossier : le format X.Y.Z interdit "../" et consorts.
        return self._root / ensure_valid_model_version(version)


def _metadata_to_dict(metadata: ModelMetadata) -> dict:
    data = asdict(metadata)
    data["trained_at"] = metadata.trained_at.isoformat()
    return data


def _metadata_from_dict(data: dict) -> ModelMetadata:
    return ModelMetadata(**{**data, "trained_at": datetime.fromisoformat(data["trained_at"])})
