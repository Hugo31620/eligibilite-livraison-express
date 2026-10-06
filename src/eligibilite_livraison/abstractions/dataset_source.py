from abc import ABC, abstractmethod

import pandas as pd


class DatasetSource(ABC):
    """Origine des commandes servant à entraîner le modèle (Strategy)."""

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Retourne les commandes historiques, cible ``express_eligible`` incluse."""
