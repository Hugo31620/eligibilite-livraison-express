"""Fabrique de l'application FastAPI.

Lancement : ``uvicorn eligibilite_livraison.api.app:create_app --factory``
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from eligibilite_livraison import PROJECT_NAME, __version__
from eligibilite_livraison.api.errors import register_error_handlers
from eligibilite_livraison.api.routes import health, orders, predictions
from eligibilite_livraison.container import AppContainer, build_container

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_TAGS = [
    {"name": "health", "description": "Sonde de vivacité et de disponibilité"},
    {"name": "orders", "description": "Collecte des commandes"},
    {"name": "predictions", "description": "Prédiction d'éligibilité à la livraison express"},
]


def create_app(container: AppContainer | None = None) -> FastAPI:
    """Crée l'application. Les tests injectent leur propre ``container``."""
    logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT)
    container = container or build_container()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container.predictors.is_ready()  # chauffe le modèle ; l'API démarre même s'il manque
        yield

    app = FastAPI(
        title=f"{PROJECT_NAME} API",
        version=__version__,
        description="API de prédiction d'éligibilité à la livraison express.",
        openapi_tags=_TAGS,
        lifespan=lifespan,
    )
    app.state.container = container
    register_error_handlers(app)
    for module in (health, orders, predictions):
        app.include_router(module.router)
    return app
