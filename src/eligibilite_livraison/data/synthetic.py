"""Jeu de données fictif (cellule 8 du notebook), exécutable sans source externe."""

import numpy as np
import pandas as pd

from eligibilite_livraison.abstractions.dataset_source import DatasetSource

ZONE_PENALTY = {"centre": 0, "proche_banlieue": 0.10, "banlieue": 0.25, "rurale": 0.45}
WEATHER_PENALTY = {"normal": 0, "pluie": 0.10, "neige": 0.25, "orage": 0.30}
PREMIUM_BONUS = 0.15


class SyntheticDatasetSource(DatasetSource):
    def __init__(self, n_rows: int = 6000, random_state: int = 42) -> None:
        if n_rows < 1:
            raise ValueError("n_rows doit être strictement positif.")
        self._n_rows = n_rows
        self._random_state = random_state

    def load(self) -> pd.DataFrame:
        rng = np.random.default_rng(self._random_state)
        orders = self._draw_orders(rng)
        probability = 1 / (1 + np.exp(-self._latent_score(orders)))
        orders["express_eligible"] = rng.binomial(1, probability)
        return orders

    def _draw_orders(self, rng: np.random.Generator) -> pd.DataFrame:
        n = self._n_rows
        order_date = pd.date_range(start="2025-01-01", end="2025-12-31", periods=n)
        hour = rng.integers(7, 23, size=n)
        day_of_week = order_date.day_of_week.to_numpy()

        return pd.DataFrame(
            {
                "order_id": [f"CMD-{i:06d}" for i in range(1, n + 1)],
                "order_date": order_date,
                "hour": hour,
                "day_of_week": day_of_week,
                "weekend": (day_of_week >= 5).astype(int),
                "distance_km": np.round(rng.gamma(shape=2.0, scale=4.0, size=n), 2),
                "order_value_eur": np.round(rng.uniform(10, 250, size=n), 2),
                "weight_kg": np.round(rng.uniform(0.2, 25, size=n), 2),
                "stock_available": rng.binomial(1, 0.85, size=n),
                "preparation_time_min": np.round(
                    rng.normal(loc=25, scale=10, size=n).clip(5, 90), 1
                ),
                "carrier_capacity": np.round(rng.uniform(0.2, 1.0, size=n), 2),
                "weather": rng.choice(list(WEATHER_PENALTY), size=n, p=[0.65, 0.20, 0.10, 0.05]),
                "delivery_zone": rng.choice(list(ZONE_PENALTY), size=n, p=[0.30, 0.30, 0.25, 0.15]),
                "customer_type": rng.choice(["standard", "premium"], size=n, p=[0.80, 0.20]),
            }
        )

    @staticmethod
    def _latent_score(data: pd.DataFrame) -> pd.Series:
        """Score latent qui simule la décision métier."""
        premium_bonus = (data["customer_type"] == "premium").astype(int) * PREMIUM_BONUS
        return (
            2.5
            - 0.18 * data["distance_km"]
            - 0.035 * data["preparation_time_min"]
            - 0.035 * data["weight_kg"]
            - data["delivery_zone"].map(ZONE_PENALTY)
            - data["weather"].map(WEATHER_PENALTY)
            + 1.8 * data["stock_available"]
            + 1.3 * data["carrier_capacity"]
            + premium_bonus
            - 0.40 * data["weekend"]
            - 0.08 * np.maximum(data["hour"] - 18, 0)
        )
