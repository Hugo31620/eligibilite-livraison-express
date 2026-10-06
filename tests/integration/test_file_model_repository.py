import pytest

from eligibilite_livraison.domain.errors import (
    InvalidModelVersionError,
    ModelAlreadyExistsError,
    ModelNotFoundError,
    ModelUnavailableError,
)
from eligibilite_livraison.infrastructure.dev.file_model_repository import (
    METADATA_FILENAME,
    MODEL_FILENAME,
    FileModelRepository,
)


@pytest.fixture
def artifact(artifacts_dir):
    return FileModelRepository(artifacts_dir).load("1.0.0")


def test_save_then_load_round_trip(tmp_path, artifact):
    repository = FileModelRepository(tmp_path)
    repository.save(artifact)

    loaded = repository.load("1.0.0")

    assert loaded.metadata == artifact.metadata
    assert (tmp_path / "1.0.0" / MODEL_FILENAME).is_file()
    assert (tmp_path / "1.0.0" / METADATA_FILENAME).is_file()


def test_a_published_version_is_immutable(tmp_path, artifact):
    repository = FileModelRepository(tmp_path)
    repository.save(artifact)
    with pytest.raises(ModelAlreadyExistsError):
        repository.save(artifact)


def test_no_temporary_folder_is_left_behind(tmp_path, artifact):
    FileModelRepository(tmp_path).save(artifact)
    assert [path.name for path in tmp_path.iterdir()] == ["1.0.0"]


def test_unknown_version_is_reported(tmp_path):
    with pytest.raises(ModelNotFoundError, match="express-train"):
        FileModelRepository(tmp_path).load("9.9.9")


def test_corrupted_model_file_is_reported(tmp_path, artifact):
    repository = FileModelRepository(tmp_path)
    repository.save(artifact)
    (tmp_path / "1.0.0" / MODEL_FILENAME).write_bytes(b"not a pickle")
    with pytest.raises(ModelUnavailableError):
        repository.load("1.0.0")


@pytest.mark.parametrize("version", ["../secret", "1.0", "latest", "1.0.0/../2.0.0"])
def test_version_cannot_escape_the_root_directory(tmp_path, version):
    with pytest.raises(InvalidModelVersionError):
        FileModelRepository(tmp_path).load(version)
