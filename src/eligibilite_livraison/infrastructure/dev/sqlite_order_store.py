"""Stockage des commandes dans SQLite (ADR-0001, option B)."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from eligibilite_livraison.abstractions.order_store import OrderStore
from eligibilite_livraison.domain.errors import (
    DuplicateOrderError,
    OrderNotFoundError,
    StorageError,
)
from eligibilite_livraison.domain.features import FEATURE_COLUMNS
from eligibilite_livraison.domain.order import OrderFeatures

_COLUMNS = ("order_id", *FEATURE_COLUMNS)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    order_id             TEXT PRIMARY KEY,
    hour                 INTEGER NOT NULL,
    day_of_week          INTEGER NOT NULL,
    weekend              INTEGER NOT NULL,
    distance_km          REAL    NOT NULL,
    order_value_eur      REAL    NOT NULL,
    weight_kg            REAL    NOT NULL,
    stock_available      INTEGER NOT NULL,
    preparation_time_min REAL    NOT NULL,
    carrier_capacity     REAL    NOT NULL,
    weather              TEXT    NOT NULL,
    delivery_zone        TEXT    NOT NULL,
    customer_type        TEXT    NOT NULL,
    created_at           TEXT    NOT NULL
)
"""

_INSERT = (
    f"INSERT INTO orders ({', '.join(_COLUMNS)}, created_at) "
    f"VALUES ({', '.join(f':{column}' for column in _COLUMNS)}, :created_at)"
)
_SELECT = f"SELECT {', '.join(_COLUMNS)} FROM orders WHERE order_id = ?"
_SELECT_ALL = f"SELECT {', '.join(_COLUMNS)} FROM orders ORDER BY created_at, rowid"


class SqliteOrderStore(OrderStore):
    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Une connexion par opération : sûr avec les threads du serveur, commit à la sortie."""
        try:
            with closing(sqlite3.connect(self._db_path, timeout=5)) as connection:
                connection.row_factory = sqlite3.Row
                with connection:
                    yield connection
        except sqlite3.Error as error:
            raise StorageError(f"Erreur du stockage des commandes : {error}") from error

    def save(self, order: OrderFeatures) -> None:
        if order.order_id is None:
            raise ValueError("order_id est obligatoire pour persister une commande.")
        created_at = datetime.now(timezone.utc).isoformat()
        row = {**order.model_dump(mode="json"), "created_at": created_at}
        with self._connect() as connection:
            try:
                connection.execute(_INSERT, row)
            except sqlite3.IntegrityError as error:
                raise DuplicateOrderError(f"La commande {order.order_id} existe déjà.") from error

    def get(self, order_id: str) -> OrderFeatures:
        with self._connect() as connection:
            row = connection.execute(_SELECT, (order_id,)).fetchone()
        if row is None:
            raise OrderNotFoundError(f"Commande inconnue : {order_id}")
        return OrderFeatures(**dict(row))

    def get_all(self) -> list[OrderFeatures]:
        with self._connect() as connection:
            rows = connection.execute(_SELECT_ALL).fetchall()
        return [OrderFeatures(**dict(row)) for row in rows]

    def is_reachable(self) -> bool:
        try:
            with self._connect() as connection:
                connection.execute("SELECT 1")
        except StorageError:
            return False
        return True
