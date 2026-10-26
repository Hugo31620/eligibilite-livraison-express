"""Contrôle d'accès des routes par rôle (ADR-0007).

Usage dans une route : ``principal: Annotated[Principal, Depends(require(Role.USER))]``.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader

from eligibilite_livraison.api.dependencies import ContainerDep
from eligibilite_livraison.domain.security import Principal, Role

API_KEY_HEADER = "X-API-Key"

_api_key_header = APIKeyHeader(
    name=API_KEY_HEADER,
    auto_error=False,  # on lève nos propres erreurs, au format Error du contrat
    description="Clé d'API personnelle (rôles guest, user, admin). Voir ADR-0007.",
)


def require(role: Role) -> Callable[..., Principal]:
    """Dépendance FastAPI : authentifie l'appelant puis vérifie qu'il a au moins ``role``."""

    def dependency(
        request: Request,
        container: ContainerDep,
        api_key: Annotated[str | None, Depends(_api_key_header)],
    ) -> Principal:
        principal = container.authentication.authenticate(api_key)
        container.authentication.authorize(principal, role)
        request.state.principal = principal  # pour l'audit (nom de la clé, jamais sa valeur)
        return principal

    return dependency


GuestDep = Annotated[Principal, Depends(require(Role.GUEST))]
UserDep = Annotated[Principal, Depends(require(Role.USER))]
AdminDep = Annotated[Principal, Depends(require(Role.ADMIN))]

AUTH_RESPONSES: dict[int | str, dict] = {
    401: {"description": "Clé d'API absente, invalide ou expirée"},
    403: {"description": "Rôle insuffisant"},
}
