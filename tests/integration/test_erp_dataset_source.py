"""Chaîne complète sur des données au format ERP : lecture → entraînement → prédiction.

Sans serveur : la collection est simulée. ``test_mongo_erp_end_to_end.py`` rejoue le même
scénario sur un vrai MongoDB quand ``MONGO_TEST_URI`` est défini.
"""

from datetime import date

import pandas as pd
import pytest

from eligibilite_livraison.domain.errors import DataQualityError
from eligibilite_livraison.domain.features import FEATURE_COLUMNS, TARGET_COLUMN
from eligibilite_livraison.domain.order import OrderFeatures
from eligibilite_livraison.infrastructure.dev.file_model_repository import FileModelRepository
from eligibilite_livraison.infrastructure.erp.translation import translate_erp_orders
from eligibilite_livraison.infrastructure.mongo.erp_dataset_source import MongoErpDatasetSource
from eligibilite_livraison.ml.training import TrainingService
from eligibilite_livraison.services.predictor import PredictorProvider
from tests.erp_fixtures import FakeOrderCollection, erp_order, erp_orders


def test_source_returns_labeled_orders_in_the_domain_vocabulary():
    data = MongoErpDatasetSource(FakeOrderCollection(erp_orders(500))).load()

    assert len(data) == 500
    assert set(data[TARGET_COLUMN]) == {0, 1}
    assert "_id" not in data.columns
    assert data["carrier_capacity"].between(0, 1).all()


def test_labels_are_reproducible():
    collection = FakeOrderCollection(erp_orders(300))
    first = MongoErpDatasetSource(collection).load()
    second = MongoErpDatasetSource(collection).load()
    assert first[TARGET_COLUMN].tolist() == second[TARGET_COLUMN].tolist()


def test_empty_source_is_reported_explicitly():
    with pytest.raises(DataQualityError, match="vide"):
        MongoErpDatasetSource(FakeOrderCollection([])).load()


def test_too_few_usable_orders_stops_the_training():
    before_2017 = [erp_order(i, date(2016, 1, 4)) for i in range(1, 50)]
    with pytest.raises(DataQualityError, match="exploitable"):
        MongoErpDatasetSource(FakeOrderCollection(before_2017), min_rows=10).load()


def test_train_then_predict_on_erp_orders(tmp_path):
    source = MongoErpDatasetSource(FakeOrderCollection(erp_orders(1500)))
    repository = FileModelRepository(tmp_path)

    metadata = TrainingService(source, repository).run("2.0.0")

    assert metadata.training_rows + metadata.test_rows == 1500
    assert metadata.metrics["roc_auc"] > 0.6

    new_orders = _as_domain_orders(erp_orders(5, start=date(2026, 10, 29), first=9000))
    predictor = PredictorProvider(repository, "2.0.0", 0.5).get()
    predictions = predictor.predict_many(new_orders)

    assert len(predictions) == 5
    assert all(0.0 <= p.probability <= 1.0 for p in predictions)
    assert {p.model_version for p in predictions} == {"2.0.0"}


def _as_domain_orders(documents) -> list[OrderFeatures]:
    """Commandes ERP du jour, traduites comme le serait une commande reçue par l'API."""
    orders, _ = translate_erp_orders(pd.DataFrame(documents))
    columns = ["order_id", *FEATURE_COLUMNS]
    return [OrderFeatures(**record) for record in orders[columns].to_dict("records")]
