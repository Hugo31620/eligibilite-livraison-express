from fastapi import APIRouter

from eligibilite_livraison.api.dependencies import ContainerDep
from eligibilite_livraison.api.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    ErrorResponse,
)
from eligibilite_livraison.api.security import AUTH_RESPONSES, UserDep
from eligibilite_livraison.domain.order import OrderFeatures
from eligibilite_livraison.domain.prediction import Prediction

router = APIRouter(prefix="/v1/predictions", tags=["predictions"])

_ERRORS = {
    **AUTH_RESPONSES,
    422: {"model": ErrorResponse, "description": "Requête invalide"},
    503: {"model": ErrorResponse, "description": "Modèle indisponible"},
}


@router.post(
    "",
    operation_id="createPrediction",
    summary="Prédire l'éligibilité express d'une commande",
    responses=_ERRORS,
)
def create_prediction(order: OrderFeatures, _: UserDep, container: ContainerDep) -> Prediction:
    """Prédiction synchrone (implémentation HTTP de la cellule 34 du notebook)."""
    return container.predictors.get().predict(order)


@router.post(
    "/batch",
    operation_id="createBatchPredictions",
    summary="Prédire un lot de commandes",
    responses=_ERRORS,
)
def create_batch_predictions(
    batch: BatchPredictionRequest, _: UserDep, container: ContainerDep
) -> BatchPredictionResponse:
    """Prédiction batch (cellule 46 du notebook) : 1 à 1000 commandes, réponses dans l'ordre."""
    predictions = container.predictors.get().predict_many(batch.orders)
    return BatchPredictionResponse(predictions=predictions, count=len(predictions))
