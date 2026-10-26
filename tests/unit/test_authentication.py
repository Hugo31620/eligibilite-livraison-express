from datetime import datetime, timedelta, timezone

import pytest

from eligibilite_livraison.domain.errors import (
    ApiKeyAlreadyExistsError,
    AuthenticationError,
    PermissionDeniedError,
)
from eligibilite_livraison.domain.security import (
    ApiKeyRecord,
    Principal,
    Role,
    generate_api_key,
    hash_api_key,
)
from eligibilite_livraison.infrastructure.dev.json_file_api_key_store import JsonFileApiKeyStore
from eligibilite_livraison.services.authentication import AuthenticationService

NOW = datetime(2026, 10, 9, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path):
    store = JsonFileApiKeyStore(tmp_path / "keys.json")
    store.add(ApiKeyRecord("alice", Role.USER, hash_api_key("sk_alice"), NOW + timedelta(days=1)))
    return store


@pytest.fixture
def service(store):
    return AuthenticationService(store, clock=lambda: NOW)


def test_valid_key_identifies_its_owner(service):
    assert service.authenticate("sk_alice") == Principal("alice", Role.USER)


@pytest.mark.parametrize("key", [None, "", "sk_bob"])
def test_missing_or_unknown_key_is_rejected(service, key):
    with pytest.raises(AuthenticationError):
        service.authenticate(key)


def test_key_is_rejected_from_its_expiry_date(store):
    expired = AuthenticationService(store, clock=lambda: NOW + timedelta(days=1))
    with pytest.raises(AuthenticationError):
        expired.authenticate("sk_alice")


def test_only_the_fingerprint_is_stored(store, tmp_path):
    content = (tmp_path / "keys.json").read_text(encoding="utf-8")
    assert "sk_alice" not in content
    assert hash_api_key("sk_alice") in content


@pytest.mark.parametrize(
    ("role", "required", "allowed"),
    [
        (Role.GUEST, Role.GUEST, True),
        (Role.GUEST, Role.USER, False),
        (Role.USER, Role.GUEST, True),
        (Role.USER, Role.ADMIN, False),
        (Role.ADMIN, Role.USER, True),
    ],
)
def test_roles_are_hierarchical(role, required, allowed):
    principal = Principal("x", role)
    if allowed:
        AuthenticationService.authorize(principal, required)
    else:
        with pytest.raises(PermissionDeniedError):
            AuthenticationService.authorize(principal, required)


def test_names_are_unique_and_keys_can_be_revoked(store):
    with pytest.raises(ApiKeyAlreadyExistsError):
        store.add(ApiKeyRecord("alice", Role.ADMIN, "x", NOW))
    assert store.revoke("alice") is True
    assert store.revoke("alice") is False
    assert store.list_all() == []


def test_missing_key_file_means_no_access(tmp_path):
    service = AuthenticationService(JsonFileApiKeyStore(tmp_path / "absent.json"))
    with pytest.raises(AuthenticationError):
        service.authenticate("sk_alice")


def test_generated_keys_are_unique_and_tagged_with_the_environment():
    first, second = generate_api_key("prod"), generate_api_key("prod")
    assert first != second
    assert first.startswith("sk_prod_")
    assert len(first) > 40
