import pytest

from eligibilite_livraison.config import Settings
from eligibilite_livraison.data.synthetic import SyntheticDatasetSource
from eligibilite_livraison.domain.errors import ConfigurationError
from eligibilite_livraison.infrastructure.dev.sqlite_order_store import SqliteOrderStore
from eligibilite_livraison.infrastructure.factory import build_infrastructure


def test_dev_uses_local_storage_and_synthetic_data(tmp_path):
    infrastructure = build_infrastructure(Settings(orders_db_path=tmp_path / "orders.db"))
    assert isinstance(infrastructure.order_store, SqliteOrderStore)
    assert isinstance(infrastructure.dataset_source, SyntheticDatasetSource)


@pytest.mark.parametrize("env", ["test", "prod"])
def test_test_and_prod_use_mongodb_without_connecting_at_startup(env):
    from eligibilite_livraison.infrastructure.mongo.erp_dataset_source import (
        MongoErpDatasetSource,
    )
    from eligibilite_livraison.infrastructure.mongo.mongo_order_store import MongoOrderStore

    # Hôte inexistant : la construction doit réussir, la connexion n'a lieu qu'à l'usage.
    settings = Settings(env=env, mongo_uri="mongodb://hote-inexistant.invalid:27017")
    infrastructure = build_infrastructure(settings)

    assert isinstance(infrastructure.order_store, MongoOrderStore)
    assert isinstance(infrastructure.dataset_source, MongoErpDatasetSource)


def test_unknown_environment_is_refused():
    with pytest.raises(ConfigurationError, match="staging"):
        build_infrastructure(Settings(env="staging"))
