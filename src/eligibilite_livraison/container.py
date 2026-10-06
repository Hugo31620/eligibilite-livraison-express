"""Racine de composition : seul endroit où l'on assemble les briques concrètes."""

from dataclasses import dataclass

from eligibilite_livraison.abstractions.order_store import OrderStore
from eligibilite_livraison.config import Settings
from eligibilite_livraison.infrastructure.factory import build_infrastructure
from eligibilite_livraison.services.orders import OrderCollectionService
from eligibilite_livraison.services.predictor import PredictorProvider


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
    order_store: OrderStore
    orders: OrderCollectionService
    predictors: PredictorProvider


def build_container(settings: Settings | None = None) -> AppContainer:
    settings = settings or Settings.from_env()
    infrastructure = build_infrastructure(settings)
    return AppContainer(
        settings=settings,
        order_store=infrastructure.order_store,
        orders=OrderCollectionService(infrastructure.order_store),
        predictors=PredictorProvider(
            infrastructure.model_repository,
            settings.model_version,
            settings.prediction_threshold,
        ),
    )
