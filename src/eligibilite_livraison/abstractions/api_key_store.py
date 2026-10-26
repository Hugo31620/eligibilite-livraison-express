from abc import ABC, abstractmethod

from eligibilite_livraison.domain.security import ApiKeyRecord


class ApiKeyReader(ABC):
    """Lecture des clés : tout ce dont l'API a besoin pour authentifier."""

    @abstractmethod
    def find_by_hash(self, key_sha256: str) -> ApiKeyRecord | None:
        """Retourne la clé dont l'empreinte correspond, ou ``None``."""


class ApiKeyWriter(ABC):
    """Écriture des clés : réservée à l'outil d'administration (``express-apikey``)."""

    @abstractmethod
    def add(self, record: ApiKeyRecord) -> None:
        """Enregistre une clé. Raises: ApiKeyAlreadyExistsError si le nom est pris."""

    @abstractmethod
    def revoke(self, name: str) -> bool:
        """Supprime la clé ``name``. Retourne ``False`` si elle n'existait pas."""

    @abstractmethod
    def list_all(self) -> list[ApiKeyRecord]:
        """Toutes les clés (empreintes uniquement)."""


class ApiKeyStore(ApiKeyReader, ApiKeyWriter):
    """Dépôt complet de clés d'API (ADR-0007)."""
