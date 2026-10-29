from abc import ABC, abstractmethod

from eligibilite_livraison.domain.model_artifact import ModelArtifact, ModelMetadata


class ModelReader(ABC):
    """Lecture des artefacts : tout ce dont l'API a besoin."""

    @abstractmethod
    def load(self, version: str) -> ModelArtifact:
        """Charge une version précise du modèle.

        Raises:
            ModelNotFoundError: la version n'existe pas.
            ModelUnavailableError: l'artefact est illisible ou corrompu.
        """

    @abstractmethod
    def list_versions(self) -> list[str]:
        """Versions publiées, de la plus ancienne à la plus récente (ordre X.Y.Z)."""


class ModelWriter(ABC):
    """Écriture des artefacts : réservée à l'entraînement."""

    @abstractmethod
    def save(self, artifact: ModelArtifact) -> ModelMetadata:
        """Enregistre une nouvelle version, jamais en écrasant une existante.

        Returns:
            Les métadonnées réellement enregistrées (complétées de l'empreinte du modèle).

        Raises:
            ModelAlreadyExistsError: la version existe déjà.
        """


class ModelRepository(ModelReader, ModelWriter):
    """Dépôt complet de modèles (cf. ADR-0002)."""
