"""Source d'entraînement : commandes de l'ERP répliquées dans la base analytique MongoDB.

Lecture seule (ADR-0008) : la source ne fait que des ``find``. La chaîne est
lecture → traduction ERP (couche anti-corruption) → étiquetage → ``TrainingService``,
qui applique ensuite le nettoyage et la validation habituels (``data/quality.py``).
"""

import logging
from collections.abc import Iterable, Mapping
from typing import Any, Protocol

import numpy as np
import pandas as pd
from pymongo.errors import PyMongoError

from eligibilite_livraison.abstractions.dataset_source import DatasetSource
from eligibilite_livraison.data.labeling import label_by_business_rule
from eligibilite_livraison.domain.errors import DataQualityError, StorageError
from eligibilite_livraison.infrastructure.erp.translation import translate_erp_orders

logger = logging.getLogger(__name__)


class OrderDocuments(Protocol):
    """Ce dont la source a besoin d'une collection : une recherche, rien d'autre."""

    def find(self, filter: Mapping[str, Any], projection: Mapping[str, Any]) -> Iterable[dict]: ...


class MongoErpDatasetSource(DatasetSource):
    def __init__(
        self, collection: OrderDocuments, *, min_rows: int = 200, random_state: int = 42
    ) -> None:
        if min_rows < 1:
            raise ValueError("min_rows doit être strictement positif.")
        self._collection = collection
        self._min_rows = min_rows
        self._random_state = random_state

    def load(self) -> pd.DataFrame:
        try:
            documents = list(self._collection.find({}, {"_id": 0}))
        except PyMongoError as error:
            raise StorageError(f"Lecture de la source ERP impossible : {error}") from error
        if not documents:
            raise DataQualityError("La source ERP est vide : l'ETL a-t-il tourné ?")

        orders, report = translate_erp_orders(pd.DataFrame(documents))
        logger.info("Source ERP : %d commandes lues, %d exploitables", report.read, report.kept)
        if report.kept < self._min_rows:
            raise DataQualityError(
                f"Seulement {report.kept} commande(s) exploitable(s) dans la source ERP "
                f"(minimum : {self._min_rows}). L'ETL a-t-il tourné ?"
            )
        return label_by_business_rule(orders, np.random.default_rng(self._random_state))
