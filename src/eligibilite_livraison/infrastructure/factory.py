"""Choix des adaptateurs selon l'environnement (Factory) : dev -> test -> prod."""

from collections.abc import Callable
from dataclasses import dataclass

from eligibilite_livraison import PROJECT_NAME
from eligibilite_livraison.abstractions.api_key_store import ApiKeyStore
from eligibilite_livraison.abstractions.dataset_source import DatasetSource
from eligibilite_livraison.abstractions.model_repository import ModelRepository
from eligibilite_livraison.abstractions.order_store import OrderStore
from eligibilite_livraison.config import Settings
from eligibilite_livraison.data.synthetic import SyntheticDatasetSource
from eligibilite_livraison.domain.errors import ConfigurationError
from eligibilite_livraison.infrastructure.dev.file_model_repository import FileModelRepository
from eligibilite_livraison.infrastructure.dev.json_file_api_key_store import JsonFileApiKeyStore
from eligibilite_livraison.infrastructure.dev.sqlite_order_store import SqliteOrderStore


@dataclass(frozen=True)
class Infrastructure:
    order_store: OrderStore
    model_repository: ModelRepository
    api_key_store: ApiKeyStore
    dataset_source: DatasetSource


def _build_dev(settings: Settings) -> Infrastructure:
    """Tout en local, données générées : aucun accès à un système réel."""
    return Infrastructure(
        order_store=SqliteOrderStore(settings.orders_db_path),
        model_repository=FileModelRepository(settings.artifacts_dir),
        api_key_store=JsonFileApiKeyStore(settings.api_keys_file),
        dataset_source=SyntheticDatasetSource(n_rows=settings.synthetic_rows),
    )


def _build_mongo(settings: Settings) -> Infrastructure:
    """Test et prod : données de l'ERP via la base analytique MongoDB (ADR-0008)."""
    # Import local : le dev et ses tests n'ouvrent jamais de client MongoDB.
    from pymongo import MongoClient

    from eligibilite_livraison.infrastructure.mongo.erp_dataset_source import (
        MongoErpDatasetSource,
    )
    from eligibilite_livraison.infrastructure.mongo.mongo_order_store import MongoOrderStore

    # La connexion est paresseuse : le client ne contacte MongoDB qu'à la première requête.
    client = MongoClient(
        settings.mongo_uri, serverSelectionTimeoutMS=3000, appname=PROJECT_NAME, tz_aware=True
    )
    database = client[settings.mongo_database]
    return Infrastructure(
        order_store=MongoOrderStore(database[settings.mongo_orders_collection]),
        model_repository=FileModelRepository(settings.artifacts_dir),
        api_key_store=JsonFileApiKeyStore(settings.api_keys_file),
        dataset_source=MongoErpDatasetSource(
            database[settings.mongo_source_collection], min_rows=settings.training_min_rows
        ),
    )


# Pour ajouter un environnement : créer infrastructure/<techno>/ puis l'enregistrer ici.
_BUILDERS: dict[str, Callable[[Settings], Infrastructure]] = {
    "dev": _build_dev,
    "test": _build_mongo,
    "prod": _build_mongo,
}


def build_infrastructure(settings: Settings) -> Infrastructure:
    try:
        builder = _BUILDERS[settings.env]
    except KeyError:
        raise ConfigurationError(
            f"Environnement {settings.env!r} non géré (disponibles : {sorted(_BUILDERS)})."
        ) from None
    return builder(settings)
