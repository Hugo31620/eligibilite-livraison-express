"""Commandes au format exact de l'ERP fourni (``erp/src/erp_simulator/generator.py``).

Reproduit le générateur du simulateur pour tester la chaîne ERP sans lancer de base.
"""

import random
from datetime import date, datetime, time, timedelta


def erp_order(sequence: int, order_date: date) -> dict[str, object]:
    rng = random.Random(sequence)
    return {
        "order_id": f"ERP-{sequence:08d}",
        # Comme MongoWriter : la date est stockée en datetime à minuit.
        "order_date": datetime.combine(order_date, time.min),
        "hour": 8 + sequence % 12,
        "day_of_week": order_date.weekday(),
        "weekend": int(order_date.weekday() >= 5) if order_date >= date(2015, 7, 1) else None,
        "distance_km": round(rng.uniform(1, 40), 2),
        "order_value_eur": round(rng.uniform(15, 250), 2),
        "weight_kg": round(rng.uniform(0.2, 25), 2),
        "stock_available": rng.randint(0, 1),
        "preparation_time_min": (
            round(rng.uniform(5, 45), 2) if order_date >= date(2017, 7, 1) else None
        ),
        "carrier_capacity": round(rng.uniform(5, 50), 2),
        "weather": rng.choice(["clear", "rain", "wind", "snow"]),
        "delivery_zone": rng.choice(["centre", "suburb", "rural"]),
        "customer_type": rng.choice(["individual", "business"]),
    }


def erp_orders(count: int, start: date = date(2023, 1, 1), first: int = 1) -> list[dict]:
    """Historique réparti jour par jour à partir de ``start`` (comme l'historique 2023+)."""
    return [erp_order(first + i, start + timedelta(days=i % 900)) for i in range(count)]


class FakeOrderCollection:
    """Collection en mémoire : seule la méthode ``find`` utilisée par la source existe."""

    def __init__(self, documents: list[dict]) -> None:
        self.documents = [dict(document, _id=i) for i, document in enumerate(documents)]
        self.writes = 0

    def find(self, filter, projection):
        assert filter == {}, "la source ERP lit toute la collection"
        hidden = {key for key, shown in projection.items() if not shown}
        return [{k: v for k, v in d.items() if k not in hidden} for d in self.documents]

    def __getattr__(self, name):  # insert_one, update_many... : interdits à la source ERP
        raise AssertionError(f"La source ERP ne doit jamais appeler {name}()")
