"""Collecte des commandes (POST /v1/orders)."""

from eligibilite_livraison.abstractions.order_store import OrderStore
from eligibilite_livraison.domain.order import OrderFeatures, new_order_id


class OrderCollectionService:
    def __init__(self, store: OrderStore) -> None:
        self._store = store

    def collect(self, order: OrderFeatures) -> str:
        """Persiste la commande et retourne son identifiant (généré si absent)."""
        order_id = order.order_id or new_order_id()
        self._store.save(order.model_copy(update={"order_id": order_id}))
        return order_id

    def get(self, order_id: str) -> OrderFeatures:
        return self._store.get(order_id)
