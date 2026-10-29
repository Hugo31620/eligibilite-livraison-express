"""Commandes collectées par l'API, stockées dans MongoDB (ADR-0008).

Elles vont dans une collection **propre à l'application** (``api_orders`` par défaut) : la
collection ``orders`` alimentée par l'ETL de l'ERP n'est jamais modifiée par l'application.
"""

import logging
from datetime import datetime, timezone

from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from eligibilite_livraison.abstractions.order_store import OrderStore
from eligibilite_livraison.domain.errors import (
    DuplicateOrderError,
    OrderNotFoundError,
    StorageError,
)
from eligibilite_livraison.domain.order import OrderFeatures

logger = logging.getLogger(__name__)

# Champs techniques jamais renvoyés au domaine.
_PROJECTION = {"_id": 0, "created_at": 0}
# MongoDB stocke les dates à la milliseconde : l'_id (croissant) départage les ex aequo.
_INSERTION_ORDER = [("created_at", 1), ("_id", 1)]


class MongoOrderStore(OrderStore):
    def __init__(self, collection: Collection) -> None:
        self._collection = collection
        self._index_ready = False

    def _ensure_unique_index(self) -> None:
        """Créé au premier usage : l'API démarre même si MongoDB n'est pas encore prêt."""
        if not self._index_ready:
            self._collection.create_index("order_id", unique=True)
            self._index_ready = True

    def save(self, order: OrderFeatures) -> None:
        if order.order_id is None:
            raise ValueError("order_id est obligatoire pour persister une commande.")
        document = {**order.model_dump(mode="json"), "created_at": datetime.now(timezone.utc)}
        try:
            self._ensure_unique_index()
            self._collection.insert_one(document)
        except DuplicateKeyError as error:
            raise DuplicateOrderError(f"La commande {order.order_id} existe déjà.") from error
        except PyMongoError as error:
            raise StorageError(f"Erreur du stockage des commandes : {error}") from error

    def get(self, order_id: str) -> OrderFeatures:
        try:
            # str() : l'identifiant ne peut jamais devenir un opérateur Mongo ($ne, $gt...).
            document = self._collection.find_one({"order_id": str(order_id)}, _PROJECTION)
        except PyMongoError as error:
            raise StorageError(f"Erreur du stockage des commandes : {error}") from error
        if document is None:
            raise OrderNotFoundError(f"Commande inconnue : {order_id}")
        return OrderFeatures(**document)

    def get_all(self) -> list[OrderFeatures]:
        try:
            documents = list(self._collection.find({}, _PROJECTION).sort(_INSERTION_ORDER))
        except PyMongoError as error:
            raise StorageError(f"Erreur du stockage des commandes : {error}") from error
        return [OrderFeatures(**document) for document in documents]

    def is_reachable(self) -> bool:
        try:
            self._collection.database.client.admin.command("ping")
        except PyMongoError:
            logger.warning("MongoDB injoignable", exc_info=True)
            return False
        return True
