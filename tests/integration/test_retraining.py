import threading

import pytest

from eligibilite_livraison import retrain_cli
from eligibilite_livraison.infrastructure.dev.file_model_repository import FileModelRepository
from eligibilite_livraison.infrastructure.mongo.erp_dataset_source import MongoErpDatasetSource
from eligibilite_livraison.ml.retraining import RetrainingService
from tests.erp_fixtures import FakeOrderCollection, erp_orders


@pytest.fixture
def erp():
    return FakeOrderCollection(erp_orders(600))


def _service(collection, repository, min_new_orders=100):
    source = MongoErpDatasetSource(collection, min_rows=50)
    return RetrainingService(source, repository, min_new_orders=min_new_orders)


def test_first_run_publishes_the_first_model(erp, tmp_path):
    repository = FileModelRepository(tmp_path)

    outcome = _service(erp, repository).run()

    assert outcome.trained is True
    assert outcome.new_model.model_version == "1.0.0"
    assert repository.list_versions() == ["1.0.0"]


def test_no_retraining_without_enough_new_orders(erp, tmp_path):
    repository = FileModelRepository(tmp_path)
    _service(erp, repository).run()
    erp.documents.extend(erp_orders(30, first=10_000))  # 30 < seuil de 100

    outcome = _service(erp, repository).run()

    assert outcome.trained is False
    assert "30 nouvelle(s) commande(s)" in outcome.reason
    assert repository.list_versions() == ["1.0.0"]


def test_enough_new_orders_publishes_the_next_minor_version(erp, tmp_path):
    repository = FileModelRepository(tmp_path)
    _service(erp, repository).run()
    erp.documents.extend(erp_orders(150, first=10_000))

    outcome = _service(erp, repository).run()

    assert outcome.trained is True
    assert outcome.previous_version == "1.0.0"
    assert outcome.new_model.model_version == "1.1.0"
    assert outcome.new_model.training_rows + outcome.new_model.test_rows == 750
    assert repository.list_versions() == ["1.0.0", "1.1.0"]


def test_versions_are_sorted_numerically(tmp_path):
    for version in ("1.9.0", "1.10.0", "1.2.0"):
        (tmp_path / version).mkdir()
        (tmp_path / version / "metadata.json").write_text("{}")
    (tmp_path / ".1.11.0.tmp").mkdir()  # écriture interrompue : ignorée
    assert FileModelRepository(tmp_path).list_versions() == ["1.2.0", "1.9.0", "1.10.0"]


def test_cli_runs_once_and_reports_failure_with_its_exit_code(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("SYNTHETIC_ROWS", "400")
    monkeypatch.setenv("ORDERS_DB_PATH", str(tmp_path / "orders.db"))

    assert retrain_cli.main([]) == 0
    assert FileModelRepository(tmp_path / "artifacts").list_versions() == ["1.0.0"]

    # Modèle précédent corrompu : la vérification échoue et le code de sortie le signale.
    (tmp_path / "artifacts" / "1.0.0" / "model.joblib").write_bytes(b"corrompu")
    assert retrain_cli.main([]) == 1


def test_watch_mode_survives_a_failed_check_and_stops_cleanly(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("ORDERS_DB_PATH", str(tmp_path / "orders.db"))
    calls = []

    def fake_run_once(service):
        calls.append(service)
        if len(calls) == 2:
            stop.set()
        return len(calls) != 1  # le premier tour échoue

    stop = threading.Event()
    monkeypatch.setattr(retrain_cli, "run_once", fake_run_once)
    monkeypatch.setattr(stop, "wait", lambda timeout: None)

    assert retrain_cli.main(["--watch"], stop=stop) == 0
    assert len(calls) == 2
