"""Cas d'usage « entraîner un modèle » : orchestre les briques sans en connaître le détail."""

import logging
from datetime import datetime, timezone

import pandas as pd
import sklearn
from sklearn.model_selection import train_test_split

from eligibilite_livraison.abstractions.dataset_source import DatasetSource
from eligibilite_livraison.abstractions.model_repository import ModelWriter
from eligibilite_livraison.data.quality import clean_orders_data, validate_dataset
from eligibilite_livraison.domain.features import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
)
from eligibilite_livraison.domain.model_artifact import (
    ModelArtifact,
    ModelMetadata,
    ensure_valid_model_version,
)
from eligibilite_livraison.ml.metrics import compute_metrics
from eligibilite_livraison.ml.pipeline import build_model_pipeline

logger = logging.getLogger(__name__)


class TrainingService:
    def __init__(
        self,
        dataset_source: DatasetSource,
        model_writer: ModelWriter,
        *,
        test_size: float = 0.20,
        random_state: int = 42,
    ) -> None:
        self._dataset_source = dataset_source
        self._model_writer = model_writer
        self._test_size = test_size
        self._random_state = random_state

    def run(self, model_version: str) -> ModelMetadata:
        """Entraîne, évalue puis enregistre le modèle sous ``model_version``."""
        ensure_valid_model_version(model_version)

        orders = self._load_clean_orders()
        x_train, x_test, y_train, y_test = self._split(orders)

        pipeline = build_model_pipeline(self._random_state)
        pipeline.fit(x_train, y_train)
        metrics = compute_metrics(
            y_test, pipeline.predict(x_test), pipeline.predict_proba(x_test)[:, 1]
        )

        metadata = ModelMetadata(
            model_version=model_version,
            trained_at=datetime.now(timezone.utc),
            sklearn_version=sklearn.__version__,
            target=TARGET_COLUMN,
            features=list(FEATURE_COLUMNS),
            numeric_features=list(NUMERIC_FEATURES),
            categorical_features=list(CATEGORICAL_FEATURES),
            metrics=metrics,
            training_rows=len(x_train),
            test_rows=len(x_test),
        )
        saved = self._model_writer.save(ModelArtifact(pipeline=pipeline, metadata=metadata))
        logger.info("Modèle %s enregistré (metrics=%s)", model_version, metrics)
        return saved

    def _load_clean_orders(self) -> pd.DataFrame:
        raw = self._dataset_source.load()
        cleaned = clean_orders_data(raw)
        validate_dataset(cleaned)
        logger.info("Données : %d lignes lues, %d conservées", len(raw), len(cleaned))
        return cleaned

    def _split(self, orders: pd.DataFrame):
        return train_test_split(
            orders[list(FEATURE_COLUMNS)],
            orders[TARGET_COLUMN],
            test_size=self._test_size,
            random_state=self._random_state,
            stratify=orders[TARGET_COLUMN],
        )
