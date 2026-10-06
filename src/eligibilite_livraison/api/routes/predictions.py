from fastapi import APIRouter

from eligibilite_livraison.api.dependencies import ContainerDep
from eligibilite_livraison.api.schemas import ErrorResponse
from eligibilite_livraison.domain.order import OrderFeatures
from eligibilite_livraison.domain.prediction import Prediction

router = APIRouter(prefix="/v1/predictions", tags=["predictions"])


@router.post(
    "",
    operation_id="createPrediction",
    summary="Prédire l'éligibilité express d'une commande",
    responses={
        422: {"model": ErrorResponse, "description": "Commande invalide"},
        503: {"model": ErrorResponse, "description": "Modèle indisponible"},
    },
)
def create_prediction(order: OrderFeatures, container: ContainerDep) -> Prediction:
    """Prédiction synchrone (implémentation HTTP de la cellule 34 du notebook)."""
    return container.predictors.get().predict(order)
