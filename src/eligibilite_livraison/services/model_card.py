"""Model card du modèle en service (cellule 55 du notebook, ``GET /v1/model``)."""

from datetime import datetime

from pydantic import BaseModel, Field

from eligibilite_livraison import PROJECT_NAME
from eligibilite_livraison.services.predictor import EligibilityPredictor

LIMITATIONS = (
    "Le jeu de données utilisé est synthétique.",
    "La décision ne doit pas être utilisée sans validation des règles métier.",
    "Les performances peuvent varier sur des données réelles.",
    "Le modèle ne remplace pas une analyse des contraintes opérationnelles.",
)


class ModelCard(BaseModel):
    project: str = Field(examples=[PROJECT_NAME])
    model_version: str = Field(examples=["1.0.0"])
    model_type: str = Field(examples=["Logistic regression"])
    task: str = Field(examples=["binary classification"])
    target: str = Field(examples=["express_eligible"])
    threshold: float = Field(examples=[0.5])
    trained_at: datetime | None = None
    features: list[str]
    metrics: dict[str, float]
    limitations: list[str] = Field(default_factory=list)


def build_model_card(predictor: EligibilityPredictor) -> ModelCard:
    metadata = predictor.metadata
    return ModelCard(
        project=PROJECT_NAME,
        model_version=metadata.model_version,
        model_type="Logistic regression",
        task="binary classification",
        target=metadata.target,
        threshold=predictor.threshold,
        trained_at=metadata.trained_at,
        features=list(metadata.features),
        metrics=metadata.metrics,
        limitations=list(LIMITATIONS),
    )
