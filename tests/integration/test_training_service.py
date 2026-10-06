import pytest

from eligibilite_livraison.data.synthetic import SyntheticDatasetSource
from eligibilite_livraison.domain.errors import InvalidModelVersionError
from eligibilite_livraison.infrastructure.dev.file_model_repository import FileModelRepository
from eligibilite_livraison.ml.training import TrainingService


def test_full_training_matches_notebook_quality(tmp_path):
    """Le notebook obtenait accuracy ≈ 0,75 et ROC-AUC ≈ 0,85 : on ne doit pas régresser."""
    repository = FileModelRepository(tmp_path)

    metadata = TrainingService(SyntheticDatasetSource(), repository).run("1.0.0")

    assert metadata.training_rows == 4800
    assert metadata.test_rows == 1200
    assert metadata.metrics["accuracy"] > 0.72
    assert metadata.metrics["roc_auc"] > 0.82
    assert repository.load("1.0.0").metadata == metadata


def test_invalid_version_is_refused_before_any_work(tmp_path):
    service = TrainingService(SyntheticDatasetSource(n_rows=100), FileModelRepository(tmp_path))
    with pytest.raises(InvalidModelVersionError):
        service.run("v1")
    assert list(tmp_path.iterdir()) == []
