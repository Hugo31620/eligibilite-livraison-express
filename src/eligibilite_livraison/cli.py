"""Commande d'entraînement : ``express-train`` (ou ``python -m eligibilite_livraison.cli``)."""

import argparse
import json
import logging
import sys
from collections.abc import Sequence

from eligibilite_livraison.config import Settings
from eligibilite_livraison.data.synthetic import SyntheticDatasetSource
from eligibilite_livraison.domain.errors import DomainError
from eligibilite_livraison.infrastructure.factory import build_infrastructure
from eligibilite_livraison.ml.training import TrainingService


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="express-train",
        description="Entraîne le modèle d'éligibilité express et l'enregistre (ADR-0002).",
    )
    parser.add_argument(
        "--model-version", help="Version X.Y.Z à publier (défaut : variable MODEL_VERSION)."
    )
    parser.add_argument(
        "--rows", type=int, default=6000, help="Taille du jeu synthétique (défaut : 6000)."
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    try:
        settings = Settings.from_env()
        service = TrainingService(
            SyntheticDatasetSource(n_rows=args.rows),
            build_infrastructure(settings).model_repository,
        )
        metadata = service.run(args.model_version or settings.model_version)
    except DomainError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1
    print(f"Modèle {metadata.model_version} enregistré dans {settings.artifacts_dir}")
    print(json.dumps(metadata.metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
