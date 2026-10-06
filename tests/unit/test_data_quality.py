import pandas as pd
import pytest

from eligibilite_livraison.data.quality import clean_orders_data, validate_dataset
from eligibilite_livraison.data.synthetic import SyntheticDatasetSource
from eligibilite_livraison.domain.errors import DataQualityError


@pytest.fixture(scope="module")
def orders() -> pd.DataFrame:
    return SyntheticDatasetSource(n_rows=300).load()


def test_valid_dataset_passes(orders):
    validate_dataset(orders)


def test_missing_column_is_reported(orders):
    with pytest.raises(DataQualityError, match="distance_km"):
        validate_dataset(orders.drop(columns=["distance_km"]))


def test_duplicate_ids_are_detected(orders):
    duplicated = pd.concat([orders, orders.iloc[[0]]], ignore_index=True)
    with pytest.raises(DataQualityError, match="dupliqués"):
        validate_dataset(duplicated)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("hour", 99),
        ("distance_km", -1.0),
        ("weight_kg", -1.0),
        ("preparation_time_min", -1.0),
        ("carrier_capacity", 1.5),
        ("stock_available", 2),
    ],
)
def test_out_of_range_values_are_detected(orders, column, value):
    broken = orders.copy()
    broken.loc[0, column] = value
    with pytest.raises(DataQualityError):
        validate_dataset(broken)


def test_clean_removes_duplicates_and_invalid_rows(orders):
    dirty = pd.concat([orders, orders.iloc[[0]]], ignore_index=True)
    dirty.loc[1, "distance_km"] = -5.0
    dirty.loc[2, "carrier_capacity"] = None

    cleaned = clean_orders_data(dirty)

    assert len(cleaned) == len(orders) - 2
    validate_dataset(cleaned)


def test_clean_does_not_modify_its_input(orders):
    before = orders.copy()
    clean_orders_data(orders)
    pd.testing.assert_frame_equal(orders, before)
