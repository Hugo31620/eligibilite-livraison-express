"""Contrôles qualité et nettoyage (cellules 14 et 18 du notebook).

Les règles sont déclarées une seule fois (``COLUMN_RULES``) et partagées par la validation
et le nettoyage : le notebook dupliquait les bornes dans les deux fonctions.
"""

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from eligibilite_livraison.domain.errors import DataQualityError
from eligibilite_livraison.domain.features import FEATURE_COLUMNS, TARGET_COLUMN

ID_COLUMN = "order_id"
DATE_COLUMN = "order_date"
REQUIRED_COLUMNS = (ID_COLUMN, DATE_COLUMN, *FEATURE_COLUMNS, TARGET_COLUMN)
ESSENTIAL_COLUMNS = (
    ID_COLUMN,
    "distance_km",
    "weight_kg",
    "stock_available",
    "preparation_time_min",
    "carrier_capacity",
    TARGET_COLUMN,
)


@dataclass(frozen=True)
class ColumnRule:
    is_valid: Callable[[pd.Series], pd.Series]
    message: str


COLUMN_RULES: dict[str, ColumnRule] = {
    "hour": ColumnRule(lambda s: s.between(0, 23), "Certaines heures sont invalides."),
    "distance_km": ColumnRule(lambda s: s.ge(0), "La distance ne peut pas être négative."),
    "weight_kg": ColumnRule(lambda s: s.ge(0), "Le poids ne peut pas être négatif."),
    "preparation_time_min": ColumnRule(
        lambda s: s.ge(0), "Le temps de préparation ne peut pas être négatif."
    ),
    "carrier_capacity": ColumnRule(
        lambda s: s.between(0, 1),
        "La capacité du transporteur doit être comprise entre 0 et 1.",
    ),
    "stock_available": ColumnRule(
        lambda s: s.isin([0, 1]),
        "La variable stock_available doit contenir uniquement 0 ou 1.",
    ),
}


def _ensure_required_columns(df: pd.DataFrame) -> None:
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise DataQualityError(f"Colonnes obligatoires absentes : {sorted(missing)}")


def validate_dataset(df: pd.DataFrame) -> None:
    """Lève ``DataQualityError`` à la première anomalie, ne retourne rien sinon."""
    _ensure_required_columns(df)

    if df[ID_COLUMN].duplicated().any():
        raise DataQualityError("Des identifiants de commande sont dupliqués.")
    if df[TARGET_COLUMN].isna().any():
        raise DataQualityError("La variable cible contient des valeurs manquantes.")
    for column, rule in COLUMN_RULES.items():
        if not rule.is_valid(df[column]).all():
            raise DataQualityError(rule.message)


def clean_orders_data(df: pd.DataFrame) -> pd.DataFrame:
    """Retourne une copie sans doublon ni ligne invalide (l'entrée n'est pas modifiée)."""
    _ensure_required_columns(df)

    cleaned = df.drop_duplicates(subset=[ID_COLUMN], keep="last").copy()
    cleaned[DATE_COLUMN] = pd.to_datetime(cleaned[DATE_COLUMN], errors="coerce")
    cleaned = cleaned.dropna(subset=list(ESSENTIAL_COLUMNS))

    is_valid_row = pd.Series(True, index=cleaned.index)
    for column, rule in COLUMN_RULES.items():
        is_valid_row &= rule.is_valid(cleaned[column])

    return cleaned[is_valid_row].reset_index(drop=True)
