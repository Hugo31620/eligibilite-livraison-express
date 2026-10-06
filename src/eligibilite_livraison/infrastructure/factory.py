"""Choix des adaptateurs selon l'environnement (Factory) : dev -> test -> prod."""

from collections.abc import Callable
from dataclasses import dataclass

from eligibilite_livraison.abstractions.model_repository import ModelRepository
from eligibilite_livraison.abstractions.order_store import OrderStore
from eligibilite_livraison.config import Settings
from eligibilite_livraison.domain.errors import ConfigurationError
from eligibilite_livraison.infrastructure.dev.file_model_repository import FileModelRepository
from eligibilite_livraison.infrastructure.dev.sqlite_order_store import SqliteOrderStore


@dataclass(frozen=True)
class Infrastructure:
    order_store: OrderStore
    model_repository: ModelRepository


def _build_dev(settings: Settings) -> Infrastructure:
    return Infrastructure(
        order_store=SqliteOrderStore(settings.orders_db_path),
        model_repository=FileModelRepository(settings.artifacts_dir),
    )


# Pour ajouter un environnement : créer infrastructure/<env>/ puis l'enregistrer ici.
_BUILDERS: dict[str, Callable[[Settings], Infrastructure]] = {"dev": _build_dev}


def build_infrastructure(settings: Settings) -> Infrastructure:
    try:
        builder = _BUILDERS[settings.env]
    except KeyError:
        raise ConfigurationError(
            f"Environnement {settings.env!r} non géré (disponibles : {sorted(_BUILDERS)})."
        ) from None
    return builder(settings)
