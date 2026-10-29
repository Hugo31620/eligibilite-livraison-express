"""Cas d'usage « réentraîner si nécessaire », appelé par l'orchestrateur (ADR-0009).

L'entraînement est une **exécution**, pas une étape de construction (séance 4) : il ne passe
pas par la CI/CD, il tourne quand il y a suffisamment de nouvelles données.

Le nouveau modèle est publié sous une nouvelle version, mais **n'est pas mis en service** :
l'API continue de servir ``MODEL_VERSION``. Passer en production reste une décision humaine
(validation des métriques, puis bascule Blue/Green, ADR-0005).
"""

import logging
from dataclasses import dataclass

import pandas as pd

from eligibilite_livraison.abstractions.dataset_source import DatasetSource
from eligibilite_livraison.abstractions.model_repository import ModelRepository
from eligibilite_livraison.data.quality import clean_orders_data
from eligibilite_livraison.domain.model_artifact import ModelMetadata, next_minor_version
from eligibilite_livraison.ml.training import TrainingService

logger = logging.getLogger(__name__)

FIRST_MODEL_VERSION = "1.0.0"


@dataclass(frozen=True)
class RetrainingOutcome:
    trained: bool
    reason: str
    usable_orders: int
    previous_version: str | None
    new_model: ModelMetadata | None = None


class _Snapshot(DatasetSource):
    """Les données déjà lues : décision et entraînement portent exactement sur le même jeu."""

    def __init__(self, data: pd.DataFrame) -> None:
        self._data = data

    def load(self) -> pd.DataFrame:
        return self._data


class RetrainingService:
    def __init__(
        self,
        dataset_source: DatasetSource,
        repository: ModelRepository,
        *,
        min_new_orders: int,
    ) -> None:
        if min_new_orders < 1:
            raise ValueError("min_new_orders doit être strictement positif.")
        self._dataset_source = dataset_source
        self._repository = repository
        self._min_new_orders = min_new_orders

    def run(self) -> RetrainingOutcome:
        data = self._dataset_source.load()
        usable = len(clean_orders_data(data))
        versions = self._repository.list_versions()

        if not versions:
            return self._train(data, FIRST_MODEL_VERSION, usable, None, "aucun modèle publié")

        latest = versions[-1]
        previous = self._repository.load(latest).metadata
        trained_on = previous.training_rows + previous.test_rows
        new_orders = usable - trained_on
        if new_orders < self._min_new_orders:
            reason = (
                f"{new_orders} nouvelle(s) commande(s) depuis le modèle {latest} "
                f"(seuil : {self._min_new_orders})"
            )
            logger.info("Pas de réentraînement : %s", reason)
            return RetrainingOutcome(False, reason, usable, latest)

        reason = f"{new_orders} nouvelles commandes depuis le modèle {latest}"
        return self._train(data, next_minor_version(latest), usable, latest, reason)

    def _train(
        self,
        data: pd.DataFrame,
        version: str,
        usable: int,
        previous_version: str | None,
        reason: str,
    ) -> RetrainingOutcome:
        logger.info("Réentraînement vers %s : %s", version, reason)
        metadata = TrainingService(_Snapshot(data), self._repository).run(version)
        logger.info(
            "Modèle %s publié (non servi). Pour le mettre en service après validation : "
            "MODEL_VERSION=%s",
            version,
            version,
        )
        return RetrainingOutcome(True, reason, usable, previous_version, metadata)
