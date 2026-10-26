import pytest

from eligibilite_livraison.apikey_cli import main
from eligibilite_livraison.domain.security import hash_api_key
from eligibilite_livraison.infrastructure.dev.json_file_api_key_store import JsonFileApiKeyStore


@pytest.fixture
def keys_file(tmp_path, monkeypatch):
    path = tmp_path / "secrets" / "api_keys.json"
    monkeypatch.setenv("API_KEYS_FILE", str(path))
    return path


def test_create_prints_the_key_once_and_stores_its_fingerprint(keys_file, capsys):
    assert main(["create", "--name", "alice", "--role", "user", "--days", "30"]) == 0

    raw_key = capsys.readouterr().out.strip().splitlines()[-1]
    assert raw_key.startswith("sk_dev_")
    [record] = JsonFileApiKeyStore(keys_file).list_all()
    assert record.key_sha256 == hash_api_key(raw_key)
    assert raw_key not in keys_file.read_text(encoding="utf-8")


def test_lifetime_cannot_exceed_90_days(keys_file):
    assert main(["create", "--name", "bob", "--role", "admin", "--days", "365"]) == 2


def test_revoke(keys_file, capsys):
    main(["create", "--name", "alice", "--role", "guest"])
    assert main(["revoke", "--name", "alice"]) == 0
    assert main(["revoke", "--name", "alice"]) == 1
