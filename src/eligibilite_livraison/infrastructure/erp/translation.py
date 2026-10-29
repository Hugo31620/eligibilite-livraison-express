"""Couche anti-corruption : commandes de l'ERP → vocabulaire du domaine (ADR-0008).

L'ERP et l'application ne parlent pas la même langue (libellés anglais, capacité du
transporteur en valeur absolue, colonnes ajoutées au fil des migrations). Toute la
traduction est concentrée ici : le domaine, le modèle et l'API n'ont jamais à connaître
le format de l'ERP. Une ligne qui ne peut pas être traduite est rejetée et comptée, jamais
devinée : on ne fait pas confiance à la qualité des données entrantes.
"""

import logging
from dataclasses import dataclass, field

import pandas as pd

from eligibilite_livraison.domain.errors import DataQualityError
from eligibilite_livraison.domain.features import FEATURE_COLUMNS, NUMERIC_FEATURES

logger = logging.getLogger(__name__)

ID_COLUMN = "order_id"
DATE_COLUMN = "order_date"

# Libellé ERP → libellé du domaine. « wind » n'a pas d'équivalent exact : il est rapproché
# d'« orage » (conditions dégradées les plus proches), voir ADR-0008.
WEATHER_FROM_ERP = {"clear": "normal", "rain": "pluie", "snow": "neige", "wind": "orage"}
ZONE_FROM_ERP = {"centre": "centre", "suburb": "banlieue", "rural": "rurale"}
CUSTOMER_FROM_ERP = {"individual": "standard", "business": "premium"}

# L'ERP exprime la capacité restante du transporteur sur 50 créneaux ; le domaine attend un
# ratio entre 0 et 1.
ERP_CARRIER_CAPACITY_MAX = 50.0

ERP_COLUMNS = (ID_COLUMN, DATE_COLUMN, *FEATURE_COLUMNS)
_CATEGORIES = {
    "weather": WEATHER_FROM_ERP,
    "delivery_zone": ZONE_FROM_ERP,
    "customer_type": CUSTOMER_FROM_ERP,
}


@dataclass(frozen=True)
class TranslationReport:
    """Bilan d'une traduction : combien de lignes lues, gardées, et pourquoi les autres non."""

    read: int
    kept: int
    rejected_by_column: dict[str, int] = field(default_factory=dict)

    @property
    def rejected(self) -> int:
        return self.read - self.kept


def translate_erp_orders(raw: pd.DataFrame) -> tuple[pd.DataFrame, TranslationReport]:
    """Traduit les commandes ERP ; retourne les lignes exploitables et le bilan."""
    missing = sorted(set(ERP_COLUMNS) - set(raw.columns) - {"weekend"})
    if missing:
        raise DataQualityError(f"Colonnes absentes de la source ERP : {missing}")

    orders = raw.copy()
    if "weekend" not in orders.columns:
        orders["weekend"] = pd.NA

    orders[DATE_COLUMN] = pd.to_datetime(orders[DATE_COLUMN], errors="coerce")
    for column in NUMERIC_FEATURES:
        orders[column] = pd.to_numeric(orders[column], errors="coerce")
    for column, vocabulary in _CATEGORIES.items():
        orders[column] = orders[column].map(vocabulary)  # libellé inconnu → NaN → rejeté

    # Colonne ajoutée en juillet 2015 : se déduit sans ambiguïté du jour de la semaine.
    orders["weekend"] = orders["weekend"].fillna((orders["day_of_week"] >= 5).astype(float))

    capacity = orders["carrier_capacity"]
    orders["carrier_capacity"] = (capacity / ERP_CARRIER_CAPACITY_MAX).where(
        capacity.between(0, ERP_CARRIER_CAPACITY_MAX)
    )

    invalid = orders[list(ERP_COLUMNS)].isna()
    rejected_by_column = {
        column: int(count) for column, count in invalid.sum().items() if count > 0
    }
    kept = orders.loc[~invalid.any(axis=1), list(ERP_COLUMNS)].reset_index(drop=True)
    for column in ("hour", "day_of_week", "weekend", "stock_available"):
        kept[column] = kept[column].astype(int)

    report = TranslationReport(read=len(raw), kept=len(kept), rejected_by_column=rejected_by_column)
    if report.rejected:
        logger.warning(
            "Source ERP : %d ligne(s) rejetée(s) sur %d (valeurs absentes ou inconnues : %s)",
            report.rejected,
            report.read,
            rejected_by_column,
        )
    return kept, report
