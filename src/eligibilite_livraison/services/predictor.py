"""Prédiction d'éligibilité (cellule 34 du notebook)."""

import logging
import threading
import time
from datetime import datetime, timezone

import pandas as pd

from eligibilite_livraison.abstractions.model_repository import ModelReader
from eligibilite_livraison.domain.errors import ModelUnavailableError
from eligibilite_livraison.domain.features import FEATURE_COLUMNS
from eligibilite_livraison.domain.model_artifact import ModelArtifact, ModelMetadata
from eligibilite_livraison.domain.order import OrderFeatures, new_order_id
from eligibilite_livraison.domain.prediction import Prediction

logger = logging.getLogger(__name__)


class EligibilityPredictor:
    """Applique un modèle entraîné à une commande. Ne sait pas d'où vient le modèle."""

    def __init__(self, artifact: ModelArtifact, threshold: float = 0.5) -> None:
        if list(artifact.metadata.features) != list(FEATURE_COLUMNS):
            raise ModelUnavailableError(
                f"Le modèle {artifact.metadata.model_version} n'a pas été entraîné "
                "avec les variables attendues par l'application."
            )
        self._pipeline = artifact.pipeline
        self._metadata = artifact.metadata
        self._threshold = threshold

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    @property
    def threshold(self) -> float:
        return self._threshold

    def predict(self, order: OrderFeatures) -> Prediction:
        return self.predict_many([order])[0]

    def predict_many(self, orders: list[OrderFeatures]) -> list[Prediction]:
        """Prédiction vectorisée d'un lot (cellule batch du notebook), dans l'ordre reçu."""
        started = time.perf_counter()
        frame = pd.DataFrame(
            [order.feature_values() for order in orders], columns=list(FEATURE_COLUMNS)
        )
        probabilities = self._pipeline.predict_proba(frame)[:, 1]
        predicted_at = datetime.now(timezone.utc)
        latency_ms = round((time.perf_counter() - started) * 1000 / len(orders), 3)
        return [
            self._to_prediction(order, float(probability), predicted_at, latency_ms)
            for order, probability in zip(orders, probabilities)
        ]

    def _to_prediction(
        self, order: OrderFeatures, probability: float, predicted_at: datetime, latency_ms: float
    ) -> Prediction:
        eligible = probability >= self._threshold
        return Prediction(
            order_id=order.order_id or new_order_id(),
            express_eligible=eligible,
            decision="oui" if eligible else "non",
            probability=round(probability, 4),
            model_version=self._metadata.model_version,
            predicted_at=predicted_at,
            latency_ms=latency_ms,
        )


class PredictorProvider:
    """Charge le modèle à la demande, le garde en mémoire et réessaie tant qu'il manque.

    Ainsi, une API démarrée avant l'entraînement devient disponible dès que le modèle
    apparaît, sans redémarrage.
    """

    def __init__(self, reader: ModelReader, model_version: str, threshold: float) -> None:
        self._reader = reader
        self._model_version = model_version
        self._threshold = threshold
        self._predictor: EligibilityPredictor | None = None
        self._lock = threading.Lock()

    def get(self) -> EligibilityPredictor:
        if self._predictor is None:
            with self._lock:
                if self._predictor is None:
                    artifact = self._reader.load(self._model_version)
                    self._predictor = EligibilityPredictor(artifact, self._threshold)
                    logger.info("Modèle %s chargé", self._model_version)
        return self._predictor

    def is_ready(self) -> bool:
        try:
            self.get()
        except ModelUnavailableError as error:
            logger.warning("Modèle indisponible : %s", error)
            return False
        return True
