from abc import ABC, abstractmethod

from eligibilite_livraison.domain.model_artifact import ModelArtifact


class ModelReader(ABC):
    """Lecture des artefacts : tout ce dont l'API a besoin."""

    @abstractmethod
    def load(self, version: str) -> ModelArtifact:
        """Charge une version précise du modèle.

        Raises:
            ModelNotFoundError: la version n'existe pas.
            ModelUnavailableError: l'artefact est illisible ou corrompu.
        """


class ModelWriter(ABC):
    """Écriture des artefacts : réservée à l'entraînement."""

    @abstractmethod
    def save(self, artifact: ModelArtifact) -> None:
        """Enregistre une nouvelle version, jamais en écrasant une existante.

        Raises:
            ModelAlreadyExistsError: la version existe déjà.
        """


class ModelRepository(ModelReader, ModelWriter):
    """Dépôt complet de modèles (cf. ADR-0002)."""
