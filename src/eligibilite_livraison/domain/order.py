"""Commande client : entité métier et règles de validation du contrat."""

from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from eligibilite_livraison.domain.features import FEATURE_COLUMNS


class Weather(str, Enum):
    NORMAL = "normal"
    PLUIE = "pluie"
    NEIGE = "neige"
    ORAGE = "orage"


class DeliveryZone(str, Enum):
    CENTRE = "centre"
    PROCHE_BANLIEUE = "proche_banlieue"
    BANLIEUE = "banlieue"
    RURALE = "rurale"


class CustomerType(str, Enum):
    STANDARD = "standard"
    PREMIUM = "premium"


class OrderFeatures(BaseModel):
    """Caractéristiques d'une commande.

    Toute variable absente ou en trop est rejetée (``extra="forbid"``), comme l'exige
    le contrat OpenAPI.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    order_id: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_-]{1,64}$",
        description="Identifiant métier de la commande. Généré par le serveur si absent.",
        examples=["CMD-000001"],
    )
    hour: int = Field(ge=0, le=23, examples=[14])
    day_of_week: int = Field(ge=0, le=6, description="0 = lundi ... 6 = dimanche", examples=[2])
    weekend: Literal[0, 1] = Field(examples=[0])
    distance_km: float = Field(ge=0, examples=[3.5])
    order_value_eur: float = Field(ge=0, examples=[89.9])
    weight_kg: float = Field(ge=0, examples=[2.4])
    stock_available: Literal[0, 1] = Field(examples=[1])
    preparation_time_min: float = Field(ge=0, examples=[18])
    carrier_capacity: float = Field(ge=0, le=1, examples=[0.85])
    weather: Weather = Field(examples=["normal"])
    delivery_zone: DeliveryZone = Field(examples=["centre"])
    customer_type: CustomerType = Field(examples=["premium"])

    def feature_values(self) -> dict[str, object]:
        """Valeurs brutes des seules variables du modèle (sans l'identifiant)."""
        return self.model_dump(mode="json", include=set(FEATURE_COLUMNS))


def new_order_id() -> str:
    return f"CMD-{uuid4().hex[:12].upper()}"
