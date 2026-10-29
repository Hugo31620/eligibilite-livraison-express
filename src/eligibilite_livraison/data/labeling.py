"""Étiquetage des commandes par la règle métier (cellule 8 du notebook).

L'ERP ne remonte pas encore le résultat réel des livraisons express (ADR-0008) : en attendant,
la cible ``express_eligible`` est simulée par la même règle que le jeu synthétique. Elle est
déclarée une seule fois ici et partagée par ``SyntheticDatasetSource`` et la source ERP (DRY).
"""

import numpy as np
import pandas as pd

from eligibilite_livraison.domain.features import TARGET_COLUMN

ZONE_PENALTY = {"centre": 0, "proche_banlieue": 0.10, "banlieue": 0.25, "rurale": 0.45}
WEATHER_PENALTY = {"normal": 0, "pluie": 0.10, "neige": 0.25, "orage": 0.30}
PREMIUM_BONUS = 0.15


def latent_score(data: pd.DataFrame) -> pd.Series:
    """Score latent qui simule la décision métier (plus il est haut, plus l'express est sûr)."""
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


def label_by_business_rule(data: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Retourne une copie de ``data`` avec la cible ``express_eligible`` tirée de la règle."""
    probability = 1 / (1 + np.exp(-latent_score(data)))
    labeled = data.copy()
    labeled[TARGET_COLUMN] = rng.binomial(1, probability.to_numpy(dtype=float))
    return labeled
