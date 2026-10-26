"""Authentification par clé d'API et contrôle des rôles (ADR-0007)."""

import logging
from collections.abc import Callable
from datetime import datetime

from eligibilite_livraison.abstractions.api_key_store import ApiKeyReader
from eligibilite_livraison.domain.errors import AuthenticationError, PermissionDeniedError
from eligibilite_livraison.domain.security import Principal, Role, hash_api_key, utc_now

logger = logging.getLogger(__name__)

# Un seul message pour « absente », « inconnue » et « expirée » : on ne renseigne pas un attaquant.
_INVALID_KEY = "Clé d'API absente, invalide ou expirée (en-tête X-API-Key)."


class AuthenticationService:
    def __init__(self, keys: ApiKeyReader, clock: Callable[[], datetime] = utc_now) -> None:
        self._keys = keys
        self._clock = clock

    def authenticate(self, raw_key: str | None) -> Principal:
        if not raw_key:
            raise AuthenticationError(_INVALID_KEY)
        record = self._keys.find_by_hash(hash_api_key(raw_key))
        if record is None:
            raise AuthenticationError(_INVALID_KEY)
        if record.is_expired(self._clock()):
            logger.warning("Clé d'API expirée utilisée : %s", record.name)
            raise AuthenticationError(_INVALID_KEY)
        return Principal(name=record.name, role=record.role)

    @staticmethod
    def authorize(principal: Principal, required: Role) -> None:
        if not principal.role.grants(required):
            logger.warning(
                "Accès refusé : %s (%s) a besoin du rôle %s",
                principal.name,
                principal.role.value,
                required.value,
            )
            raise PermissionDeniedError(f"Le rôle {required.value!r} est requis.")
