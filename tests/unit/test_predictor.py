import pytest

from eligibilite_livraison.domain.errors import ModelNotFoundError, ModelUnavailableError
from eligibilite_livraison.domain.model_artifact import ModelArtifact
from eligibilite_livraison.domain.order import OrderFeatures
from eligibilite_livraison.infrastructure.dev.file_model_repository import FileModelRepository
from eligibilite_livraison.services.predictor import EligibilityPredictor, PredictorProvider


@pytest.fixture
def artifact(artifacts_dir) -> ModelArtifact:
    return FileModelRepository(artifacts_dir).load("1.0.0")


def test_prediction_is_consistent(artifact, valid_order):
    prediction = EligibilityPredictor(artifact).predict(OrderFeatures(**valid_order))

    assert prediction.decision in {"oui", "non"}
    assert prediction.express_eligible == (prediction.decision == "oui")
    assert 0 <= prediction.probability <= 1
    assert prediction.model_version == "1.0.0"


def test_easy_order_is_eligible_and_hard_order_is_not(artifact, valid_order, hard_order):
    predictor = EligibilityPredictor(artifact)
    assert predictor.predict(OrderFeatures(**valid_order)).decision == "oui"
    assert predictor.predict(OrderFeatures(**hard_order)).decision == "non"


def test_threshold_drives_the_decision(artifact, valid_order):
    order = OrderFeatures(**valid_order)
    assert EligibilityPredictor(artifact, threshold=0.0).predict(order).decision == "oui"
    assert EligibilityPredictor(artifact, threshold=1.0).predict(order).decision == "non"


def test_order_id_is_kept_or_generated(artifact, valid_order):
    predictor = EligibilityPredictor(artifact)
    assert predictor.predict(OrderFeatures(order_id="CMD-7", **valid_order)).order_id == "CMD-7"
    assert predictor.predict(OrderFeatures(**valid_order)).order_id.startswith("CMD-")


def test_model_trained_on_other_features_is_refused(artifact):
    incompatible = ModelArtifact(
        pipeline=artifact.pipeline,
        metadata=type(artifact.metadata)(**{**artifact.metadata.__dict__, "features": ["x"]}),
    )
    with pytest.raises(ModelUnavailableError):
        EligibilityPredictor(incompatible)


def test_provider_reports_missing_model_then_recovers(tmp_path, artifacts_dir):
    repository = FileModelRepository(tmp_path)
    provider = PredictorProvider(repository, "1.0.0", threshold=0.5)

    assert provider.is_ready() is False
    with pytest.raises(ModelNotFoundError):
        provider.get()

    repository.save(FileModelRepository(artifacts_dir).load("1.0.0"))
    assert provider.is_ready() is True
    assert provider.get() is provider.get()
