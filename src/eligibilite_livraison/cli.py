"""Commande d'entraînement : ``express-train`` (ou ``python -m eligibilite_livraison.cli``)."""

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from dataclasses import replace

from eligibilite_livraison.config import Settings
from eligibilite_livraison.domain.errors import DomainError
from eligibilite_livraison.infrastructure.factory import build_infrastructure
from eligibilite_livraison.ml.training import TrainingService


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="express-train",
        description="Entraîne le modèle d'éligibilité express (ADR-0002, ADR-0008).",
    )
    parser.add_argument(
        "--model-version", help="Version X.Y.Z à publier (défaut : variable MODEL_VERSION)."
    )
    parser.add_argument(
        "--rows",
        type=int,
        help="Dev uniquement : taille du jeu synthétique (défaut : SYNTHETIC_ROWS ou 6000).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    try:
        settings = Settings.from_env()
        if args.rows is not None:
            settings = replace(settings, synthetic_rows=args.rows)
        # Dev : jeu synthétique ; test / prod : commandes de l'ERP (ADR-0008).
        infrastructure = build_infrastructure(settings)
        service = TrainingService(infrastructure.dataset_source, infrastructure.model_repository)
        metadata = service.run(args.model_version or settings.model_version)
    except DomainError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1
    print(f"Modèle {metadata.model_version} enregistré dans {settings.artifacts_dir}")
    print(json.dumps(metadata.metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
