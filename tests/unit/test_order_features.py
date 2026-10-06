import pytest
from pydantic import ValidationError

from eligibilite_livraison.domain.features import FEATURE_COLUMNS
from eligibilite_livraison.domain.order import OrderFeatures


def test_valid_order_is_accepted(valid_order):
    order = OrderFeatures(**valid_order)
    assert order.order_id is None
    assert order.weather.value == "normal"


def test_feature_columns_match_model_fields():
    assert set(OrderFeatures.model_fields) == set(FEATURE_COLUMNS) | {"order_id"}


def test_feature_values_excludes_identifier_and_keeps_plain_values(valid_order):
    values = OrderFeatures(order_id="CMD-1", **valid_order).feature_values()
    assert list(values) == list(FEATURE_COLUMNS) or set(values) == set(FEATURE_COLUMNS)
    assert "order_id" not in values
    assert values["weather"] == "normal"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("hour", 24),
        ("hour", -1),
        ("day_of_week", 7),
        ("weekend", 2),
        ("distance_km", -0.1),
        ("order_value_eur", -1),
        ("weight_kg", -1),
        ("stock_available", 3),
        ("preparation_time_min", -5),
        ("carrier_capacity", 1.2),
        ("weather", "grele"),
        ("delivery_zone", "lune"),
        ("customer_type", "vip"),
        ("order_id", "../etc/passwd"),
        ("order_id", ""),
    ],
)
def test_out_of_contract_values_are_rejected(valid_order, field, value):
    with pytest.raises(ValidationError):
        OrderFeatures(**{**valid_order, field: value})


@pytest.mark.parametrize("missing", ["hour", "distance_km", "weather", "customer_type"])
def test_missing_feature_is_rejected(valid_order, missing):
    del valid_order[missing]
    with pytest.raises(ValidationError):
        OrderFeatures(**valid_order)


def test_unknown_feature_is_rejected(valid_order):
    with pytest.raises(ValidationError):
        OrderFeatures(**valid_order, coupon="X")
