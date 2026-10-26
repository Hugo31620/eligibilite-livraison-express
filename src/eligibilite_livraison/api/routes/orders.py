from fastapi import APIRouter

from eligibilite_livraison.api.dependencies import ContainerDep
from eligibilite_livraison.api.schemas import ErrorResponse, OrderAccepted
from eligibilite_livraison.api.security import AUTH_RESPONSES, AdminDep, UserDep
from eligibilite_livraison.domain.order import OrderFeatures

router = APIRouter(prefix="/v1/orders", tags=["orders"])


@router.post(
    "",
    status_code=202,
    operation_id="createOrder",
    summary="Enregistrer une commande à prédire",
    responses={
        **AUTH_RESPONSES,
        422: {"model": ErrorResponse, "description": "Commande invalide"},
        500: {"model": ErrorResponse, "description": "Erreur interne"},
    },
)
def create_order(order: OrderFeatures, _: UserDep, container: ContainerDep) -> OrderAccepted:
    """Collecte de données : la commande est persistée via l'``OrderStore`` (rôle ``user``)."""
    return OrderAccepted(order_id=container.orders.collect(order))


@router.get(
    "/{order_id}",
    operation_id="getOrder",
    summary="Relire une commande collectée",
    responses={
        **AUTH_RESPONSES,
        404: {"model": ErrorResponse, "description": "Commande inconnue"},
    },
)
def get_order(order_id: str, _: AdminDep, container: ContainerDep) -> OrderFeatures:
    """Relire une donnée client collectée est réservé au rôle ``admin`` (ADR-0007)."""
    return container.orders.get(order_id)
