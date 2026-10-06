import pandas as pd
import pytest

from eligibilite_livraison.data.synthetic import SyntheticDatasetSource
from eligibilite_livraison.domain.features import FEATURE_COLUMNS, TARGET_COLUMN


def test_dataset_has_expected_shape_and_columns():
    data = SyntheticDatasetSource(n_rows=200).load()
    assert len(data) == 200
    assert {"order_id", "order_date", TARGET_COLUMN, *FEATURE_COLUMNS} <= set(data.columns)
    assert set(data[TARGET_COLUMN]) <= {0, 1}


def test_same_seed_gives_same_dataset():
    first = SyntheticDatasetSource(n_rows=200, random_state=7).load()
    second = SyntheticDatasetSource(n_rows=200, random_state=7).load()
    pd.testing.assert_frame_equal(first, second)


def test_target_distribution_matches_notebook():
    """Le notebook annonçait ~78,85 % de commandes éligibles sur 6000 lignes."""
    rate = SyntheticDatasetSource().load()[TARGET_COLUMN].mean()
    assert rate == pytest.approx(0.7885, abs=0.02)


def test_non_positive_size_is_rejected():
    with pytest.raises(ValueError, match="n_rows"):
        SyntheticDatasetSource(n_rows=0)
