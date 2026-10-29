"""Entraînement de bout en bout sur un vrai MongoDB, alimenté comme le fait le simulateur ERP.

Exécuté seulement si ``MONGO_TEST_URI`` est défini (CI, ``docker-compose.test.yml``).
"""

import os
import uuid

import pytest

from eligibilite_livraison.config import Settings
from eligibilite_livraison.infrastructure.factory import build_infrastructure
from eligibilite_livraison.ml.training import TrainingService
from tests.erp_fixtures import erp_orders

MONGO_TEST_URI = os.environ.get("MONGO_TEST_URI")

pytestmark = pytest.mark.skipif(not MONGO_TEST_URI, reason="MONGO_TEST_URI non défini")


@pytest.fixture
def mongo_settings(tmp_path, api_keys_file):
    from pymongo import MongoClient

    database = f"test_{uuid.uuid4().hex[:8]}"
    client = MongoClient(MONGO_TEST_URI, serverSelectionTimeoutMS=3000)
    client[database]["orders"].insert_many(erp_orders(800))  # rôle de l'ETL / du simulateur
    yield Settings(
        env="test",
        artifacts_dir=tmp_path / "artifacts",
        api_keys_file=api_keys_file,
        mongo_uri=MONGO_TEST_URI,
        mongo_database=database,
    )
    client.drop_database(database)
    client.close()


def test_training_reads_the_erp_collection_without_modifying_it(mongo_settings):
    from pymongo import MongoClient

    infrastructure = build_infrastructure(mongo_settings)
    metadata = TrainingService(infrastructure.dataset_source, infrastructure.model_repository).run(
        "1.0.0"
    )

    assert metadata.training_rows + metadata.test_rows == 800
    assert infrastructure.order_store.is_reachable()
    erp = MongoClient(MONGO_TEST_URI)[mongo_settings.mongo_database]["orders"]
    assert erp.count_documents({}) == 800
    assert erp.count_documents({"express_eligible": {"$exists": True}}) == 0
