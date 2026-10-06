"""Pipeline scikit-learn (cellule 24 du notebook)."""

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from eligibilite_livraison.domain.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES


def build_model_pipeline(random_state: int = 42) -> Pipeline:
    numeric = Pipeline(
        [("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("numeric", numeric, list(NUMERIC_FEATURES)),
            ("categorical", categorical, list(CATEGORICAL_FEATURES)),
        ]
    )
    classifier = LogisticRegression(
        max_iter=1000, class_weight="balanced", random_state=random_state
    )
    return Pipeline([("preprocessor", preprocessor), ("classifier", classifier)])
