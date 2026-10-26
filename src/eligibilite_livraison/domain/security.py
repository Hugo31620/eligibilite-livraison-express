"""Rôles et clés d'API (ADR-0007) : qui a le droit de faire quoi."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class Role(str, Enum):
    """Rôles hiérarchiques : chaque rôle hérite des droits du rôle inférieur."""

    GUEST = "guest"  # lecture des métadonnées du modèle
    USER = "user"  # + prédire et déposer des commandes
    ADMIN = "admin"  # + relire les données clients collectées

    @property
    def level(self) -> int:
        return _LEVELS[self]

    def grants(self, required: "Role") -> bool:
        return self.level >= required.level


_LEVELS = {Role.GUEST: 0, Role.USER: 1, Role.ADMIN: 2}

API_KEY_PREFIX = "sk"
MAX_KEY_LIFETIME_DAYS = 90


@dataclass(frozen=True)
class ApiKeyRecord:
    """Ce qui est stocké : jamais la clé elle-même, seulement son empreinte SHA-256."""

    name: str
    role: Role
    key_sha256: str
    expires_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at


@dataclass(frozen=True)
class Principal:
    """Appelant authentifié. Le nom sert à l'audit ; la clé n'est jamais journalisée."""

    name: str
    role: Role


def hash_api_key(raw_key: str) -> str:
    # Clé aléatoire de 256 bits : un SHA-256 simple suffit (pas de mot de passe à étirer).
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key(env: str) -> str:
    """Ex. ``sk_dev_Qm9...`` : l'environnement est lisible, le secret ne l'est pas."""
    return f"{API_KEY_PREFIX}_{env}_{secrets.token_urlsafe(32)}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
