from fastapi import APIRouter, Response

from eligibilite_livraison import PROJECT_NAME, __version__
from eligibilite_livraison.api.dependencies import ContainerDep
from eligibilite_livraison.api.schemas import HealthStatus, ReadinessStatus

router = APIRouter(tags=["health"])


@router.get("/health", operation_id="getHealth", summary="Sonde de vivacité")
def get_health() -> HealthStatus:
    """Répond 200 si le processus est vivant. Ne dépend d'aucune brique externe."""
    return HealthStatus(service=PROJECT_NAME, version=__version__)


@router.get(
    "/health/ready",
    operation_id="getReadiness",
    summary="Sonde de disponibilité",
    responses={503: {"model": ReadinessStatus, "description": "Le service n'est pas prêt"}},
)
def get_readiness(container: ContainerDep, response: Response) -> ReadinessStatus:
    """Répond 200 uniquement si une prédiction est possible (modèle chargé, stockage joignable)."""
    model_ready = container.predictors.is_ready()
    store_ready = container.order_store.is_reachable()
    ready = model_ready and store_ready
    if not ready:
        response.status_code = 503
    return ReadinessStatus(
        status="ready" if ready else "not_ready",
        checks={
            "model": "loaded" if model_ready else "not_loaded",
            "order_store": "reachable" if store_ready else "unreachable",
        },
        version=__version__,
    )
