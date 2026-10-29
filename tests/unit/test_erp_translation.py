from datetime import date

import pandas as pd
import pytest

from eligibilite_livraison.domain.errors import DataQualityError
from eligibilite_livraison.domain.features import FEATURE_COLUMNS
from eligibilite_livraison.domain.order import OrderFeatures
from eligibilite_livraison.infrastructure.erp.translation import translate_erp_orders
from tests.erp_fixtures import erp_order, erp_orders


def _translate(documents):
    return translate_erp_orders(pd.DataFrame(documents))


def test_erp_vocabulary_is_translated_into_the_domain_vocabulary():
    orders, report = _translate(erp_orders(300))

    assert report.read == report.kept == 300
    assert set(orders["weather"]) <= {"normal", "pluie", "neige", "orage"}
    assert set(orders["delivery_zone"]) <= {"centre", "banlieue", "rurale"}
    assert set(orders["customer_type"]) <= {"standard", "premium"}


@pytest.mark.parametrize(
    ("erp_value", "expected"),
    [("clear", "normal"), ("rain", "pluie"), ("snow", "neige"), ("wind", "orage")],
)
def test_each_erp_weather_has_a_fixed_translation(erp_value, expected):
    orders, _ = _translate([{**erp_order(1, date(2024, 3, 4)), "weather": erp_value}])
    assert orders.loc[0, "weather"] == expected


def test_carrier_capacity_becomes_a_ratio():
    document = {**erp_order(1, date(2024, 3, 4)), "carrier_capacity": 40.0}
    orders, _ = _translate([document])
    assert orders.loc[0, "carrier_capacity"] == pytest.approx(0.8)


def test_every_translated_row_satisfies_the_domain_contract():
    orders, _ = _translate(erp_orders(200))
    for record in orders[list(FEATURE_COLUMNS)].to_dict("records"):
        OrderFeatures(**record)  # lève une ValidationError si une valeur sort du contrat


def test_missing_weekend_before_the_2015_migration_is_derived_from_the_day():
    saturday = date(2015, 2, 7)
    document = {**erp_order(1, saturday), "preparation_time_min": 20.0}
    assert document["weekend"] is None

    orders, report = _translate([document])

    assert report.kept == 1
    assert orders.loc[0, "weekend"] == 1


def test_orders_without_preparation_time_are_rejected_not_guessed():
    before_2017 = erp_order(1, date(2016, 5, 2))
    assert before_2017["preparation_time_min"] is None

    orders, report = _translate([before_2017, erp_order(2, date(2024, 5, 2))])

    assert report.kept == 1
    assert report.rejected_by_column == {"preparation_time_min": 1}
    assert orders.loc[0, "order_id"] == "ERP-00000002"


def test_unknown_labels_and_out_of_range_capacity_are_rejected_and_counted():
    good = erp_order(1, date(2024, 1, 2))
    documents = [
        good,
        {**erp_order(2, date(2024, 1, 2)), "weather": "tornado"},
        {**erp_order(3, date(2024, 1, 2)), "delivery_zone": "moon"},
        {**erp_order(4, date(2024, 1, 2)), "carrier_capacity": 75},
        {**erp_order(5, date(2024, 1, 2)), "distance_km": "loin"},
    ]

    orders, report = _translate(documents)

    assert list(orders["order_id"]) == ["ERP-00000001"]
    assert report.rejected == 4
    assert report.rejected_by_column == {
        "weather": 1,
        "delivery_zone": 1,
        "carrier_capacity": 1,
        "distance_km": 1,
    }


def test_a_source_missing_a_column_is_refused():
    documents = [{k: v for k, v in erp_order(1, date(2024, 1, 2)).items() if k != "weather"}]
    with pytest.raises(DataQualityError, match="weather"):
        _translate(documents)


def test_the_raw_erp_data_is_left_untouched():
    raw = pd.DataFrame(erp_orders(10))
    snapshot = raw.copy()
    translate_erp_orders(raw)
    pd.testing.assert_frame_equal(raw, snapshot)
