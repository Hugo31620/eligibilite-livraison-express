"""Évaluation du modèle (cellule 26 du notebook)."""

from collections.abc import Sequence

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def compute_metrics(
    y_true: Sequence[int], y_pred: Sequence[int], y_proba: Sequence[float]
) -> dict[str, float]:
    """Métriques de classification, converties en ``float`` natifs (sérialisables en JSON)."""
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_proba)),
    }
