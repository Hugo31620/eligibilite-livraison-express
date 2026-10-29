from abc import ABC, abstractmethod

from eligibilite_livraison.domain.order import OrderFeatures


class OrderStore(ABC):
    """Stockage des commandes clients collectées (cf. ADR-0001, ADR-0008)."""

    @abstractmethod
    def save(self, order: OrderFeatures) -> None:
        """Persiste une commande dont ``order_id`` est renseigné.

        Raises:
            DuplicateOrderError: l'identifiant existe déjà.
            StorageError: le support de stockage a échoué.
        """

    @abstractmethod
    def get(self, order_id: str) -> OrderFeatures:
        """Relit une commande.

        Raises:
            OrderNotFoundError: l'identifiant est inconnu.
        """

    @abstractmethod
    def get_all(self) -> list[OrderFeatures]:
        """Toutes les commandes collectées, de la plus ancienne à la plus récente."""

    @abstractmethod
    def is_reachable(self) -> bool:
        """Indique si le stockage répond (sonde de disponibilité)."""
