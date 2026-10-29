"""Tests de contrat de ``OrderStore`` : rejoués tels quels sur chaque adaptateur.

- ``sqlite`` : dev (ADR-0001) ;
- ``mongomock`` : MongoDB en mémoire, toujours exécuté ;
- ``mongodb`` : vrai serveur MongoDB, seulement si ``MONGO_TEST_URI`` est défini (CI, compose de
  test). Chaque test y utilise une base jetable, supprimée à la fin.
"""

import os
import uuid

import pytest

from eligibilite_livraison.abstractions.order_store import OrderStore
from eligibilite_livraison.domain.errors import DuplicateOrderError, OrderNotFoundError
from eligibilite_livraison.domain.order import OrderFeatures
from eligibilite_livraison.infrastructure.dev.sqlite_order_store import SqliteOrderStore

MONGO_TEST_URI = os.environ.get("MONGO_TEST_URI")


def _mongomock_store():
    mongomock = pytest.importorskip("mongomock")
    from eligibilite_livraison.infrastructure.mongo.mongo_order_store import MongoOrderStore

    return MongoOrderStore(mongomock.MongoClient()["livraison_express"]["api_orders"])


@pytest.fixture
def mongodb_store():
    if not MONGO_TEST_URI:
        pytest.skip("MONGO_TEST_URI non défini : pas de serveur MongoDB pour ce test")
    from pymongo import MongoClient

    from eligibilite_livraison.infrastructure.mongo.mongo_order_store import MongoOrderStore

    client = MongoClient(MONGO_TEST_URI, serverSelectionTimeoutMS=3000, tz_aware=True)
    database = f"test_{uuid.uuid4().hex[:8]}"
    yield MongoOrderStore(client[database]["api_orders"])
    client.drop_database(database)
    client.close()


@pytest.fixture(params=["sqlite", "mongomock", "mongodb"])
def store(request, tmp_path) -> OrderStore:
    if request.param == "sqlite":
        return SqliteOrderStore(tmp_path / "nested" / "orders.db")
    if request.param == "mongomock":
        return _mongomock_store()
    return request.getfixturevalue("mongodb_store")


def test_saved_order_can_be_read_back(store, valid_order):
    order = OrderFeatures(order_id="CMD-000001", **valid_order)
    store.save(order)
    assert store.get("CMD-000001") == order


def test_unknown_order_raises(store):
    with pytest.raises(OrderNotFoundError):
        store.get("CMD-XXXX")


def test_duplicate_identifier_is_refused_and_keeps_the_first_order(store, valid_order):
    store.save(OrderFeatures(order_id="CMD-1", **valid_order))
    with pytest.raises(DuplicateOrderError):
        store.save(OrderFeatures(order_id="CMD-1", **{**valid_order, "hour": 9}))
    assert store.get("CMD-1").hour == 14


def test_order_without_identifier_cannot_be_persisted(store, valid_order):
    with pytest.raises(ValueError, match="order_id"):
        store.save(OrderFeatures(**valid_order))


def test_get_all_returns_every_order_in_insertion_order(store, valid_order):
    assert store.get_all() == []
    for order_id in ("CMD-B", "CMD-A", "CMD-C"):
        store.save(OrderFeatures(order_id=order_id, **valid_order))
    assert [order.order_id for order in store.get_all()] == ["CMD-B", "CMD-A", "CMD-C"]


def test_store_is_reachable(store):
    assert store.is_reachable() is True


def test_data_survives_a_new_instance(tmp_path, valid_order):
    path = tmp_path / "orders.db"
    SqliteOrderStore(path).save(OrderFeatures(order_id="CMD-1", **valid_order))
    assert SqliteOrderStore(path).get("CMD-1").order_id == "CMD-1"


@pytest.mark.parametrize("attack", ["x' OR '1'='1", '{"$ne": null}', "$where"])
def test_injection_attempt_in_identifier_is_harmless(store, valid_order, attack):
    store.save(OrderFeatures(order_id="CMD-1", **valid_order))
    with pytest.raises(OrderNotFoundError):
        store.get(attack)
