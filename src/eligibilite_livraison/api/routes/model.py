from fastapi import APIRouter

from eligibilite_livraison.api.dependencies import ContainerDep
from eligibilite_livraison.api.schemas import ErrorResponse
from eligibilite_livraison.api.security import AUTH_RESPONSES, GuestDep
from eligibilite_livraison.services.model_card import ModelCard, build_model_card

router = APIRouter(prefix="/v1/model", tags=["model"])


@router.get(
    "",
    operation_id="getModelCard",
    summary="Métadonnées et métriques du modèle en service",
    responses={
        **AUTH_RESPONSES,
        503: {"model": ErrorResponse, "description": "Modèle indisponible"},
    },
)
def get_model_card(_: GuestDep, container: ContainerDep) -> ModelCard:
    """Model card (cellule 55 du notebook). Accessible dès le rôle ``guest``."""
    return build_model_card(container.predictors.get())
