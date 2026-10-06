"""Résultat d'une prédiction (cellule 34 du notebook)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Prediction(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_id: str = Field(examples=["CMD-000001"])
    express_eligible: bool
    decision: Literal["oui", "non"]
    probability: float = Field(ge=0, le=1, examples=[0.8734])
    model_version: str = Field(examples=["1.0.0"])
    predicted_at: datetime
    latency_ms: float | None = Field(
        default=None, description="Temps de calcul de la prédiction, pour l'observabilité"
    )
