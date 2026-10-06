"""Tests de contrat de ``OrderStore`` : à rejouer tels quels sur tout nouvel adaptateur.

Pour ajouter PostgreSQL (ADR-0001), il suffira d'ajouter sa fabrique dans ``params``.
"""

import pytest

from eligibilite_livraison.abstractions.order_store import OrderStore
from eligibilite_livraison.domain.errors import DuplicateOrderError, OrderNotFoundError
from eligibilite_livraison.domain.order import OrderFeatures
from eligibilite_livraison.infrastructure.dev.sqlite_order_store import SqliteOrderStore


@pytest.fixture(params=["sqlite"])
def store(request, tmp_path) -> OrderStore:
    factories = {"sqlite": lambda: SqliteOrderStore(tmp_path / "nested" / "orders.db")}
    return factories[request.param]()


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


def test_store_is_reachable(store):
    assert store.is_reachable() is True


def test_data_survives_a_new_instance(tmp_path, valid_order):
    path = tmp_path / "orders.db"
    SqliteOrderStore(path).save(OrderFeatures(order_id="CMD-1", **valid_order))
    assert SqliteOrderStore(path).get("CMD-1").order_id == "CMD-1"


def test_sql_injection_attempt_in_identifier_is_harmless(store, valid_order):
    with pytest.raises(OrderNotFoundError):
        store.get("x' OR '1'='1")
