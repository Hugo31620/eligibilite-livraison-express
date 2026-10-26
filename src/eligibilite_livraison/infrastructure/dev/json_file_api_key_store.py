"""Clés d'API dans un fichier JSON d'empreintes (ADR-0007).

Le fichier ne contient **que des empreintes SHA-256**, jamais les clés. En local il vit dans
``secrets/`` (ignoré par Git) ; en production c'est un secret Key Vault monté en lecture seule.
Il est relu dès qu'il change : une rotation de clé ne demande pas de redémarrer l'API.
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path

from eligibilite_livraison.abstractions.api_key_store import ApiKeyStore
from eligibilite_livraison.domain.errors import ApiKeyAlreadyExistsError, ConfigurationError
from eligibilite_livraison.domain.security import ApiKeyRecord, Role


class JsonFileApiKeyStore(ApiKeyStore):
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._cache: dict[str, ApiKeyRecord] = {}
        self._cache_mtime: float | None = None

    def find_by_hash(self, key_sha256: str) -> ApiKeyRecord | None:
        return self._records_by_hash().get(key_sha256)

    def list_all(self) -> list[ApiKeyRecord]:
        return list(self._records_by_hash().values())

    def add(self, record: ApiKeyRecord) -> None:
        records = self.list_all()
        if any(existing.name == record.name for existing in records):
            raise ApiKeyAlreadyExistsError(
                f"Une clé nommée {record.name!r} existe déjà : révoquez-la ou changez de nom."
            )
        self._write([*records, record])

    def revoke(self, name: str) -> bool:
        records = self.list_all()
        kept = [record for record in records if record.name != name]
        if len(kept) == len(records):
            return False
        self._write(kept)
        return True

    def _records_by_hash(self) -> dict[str, ApiKeyRecord]:
        try:
            mtime = self._path.stat().st_mtime
        except FileNotFoundError:
            return {}  # aucun fichier = aucune clé = tout appel protégé est refusé
        with self._lock:
            if mtime != self._cache_mtime:
                self._cache = {record.key_sha256: record for record in self._read()}
                self._cache_mtime = mtime
            return self._cache

    def _read(self) -> list[ApiKeyRecord]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return [_from_dict(item) for item in raw]
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ConfigurationError(f"Fichier de clés {self._path} invalide : {error}") from error

    def _write(self, records: list[ApiKeyRecord]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        staging = self._path.with_suffix(".tmp")
        staging.write_text(
            json.dumps([_to_dict(record) for record in records], indent=2), encoding="utf-8"
        )
        os.replace(staging, self._path)


def _to_dict(record: ApiKeyRecord) -> dict:
    return {
        "name": record.name,
        "role": record.role.value,
        "key_sha256": record.key_sha256,
        "expires_at": record.expires_at.isoformat(),
    }


def _from_dict(data: dict) -> ApiKeyRecord:
    return ApiKeyRecord(
        name=data["name"],
        role=Role(data["role"]),
        key_sha256=data["key_sha256"],
        expires_at=datetime.fromisoformat(data["expires_at"]),
    )
