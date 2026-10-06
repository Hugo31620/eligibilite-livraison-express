"""Variables du modèle : unique source de vérité (cellule 20 du notebook)."""

TARGET_COLUMN = "express_eligible"

NUMERIC_FEATURES: tuple[str, ...] = (
    "hour",
    "day_of_week",
    "weekend",
    "distance_km",
    "order_value_eur",
    "weight_kg",
    "stock_available",
    "preparation_time_min",
    "carrier_capacity",
)

CATEGORICAL_FEATURES: tuple[str, ...] = (
    "weather",
    "delivery_zone",
    "customer_type",
)

FEATURE_COLUMNS: tuple[str, ...] = NUMERIC_FEATURES + CATEGORICAL_FEATURES
