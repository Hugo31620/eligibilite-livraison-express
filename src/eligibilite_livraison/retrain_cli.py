"""Orchestration du réentraînement : ``express-retrain`` (ADR-0009).

- ``express-retrain`` : une vérification, puis sortie (pour un planificateur externe :
  cron, Azure Container Apps Job, tâche Airflow…) ;
- ``express-retrain --watch`` : planificateur intégré, une vérification toutes les
  ``RETRAIN_INTERVAL_MINUTES`` (service ``retrainer`` des fichiers docker compose).
"""

import argparse
import logging
import signal
import sys
import threading
from collections.abc import Sequence

from eligibilite_livraison.config import Settings
from eligibilite_livraison.domain.errors import DomainError
from eligibilite_livraison.infrastructure.factory import build_infrastructure
from eligibilite_livraison.ml.retraining import RetrainingService

logger = logging.getLogger("express-retrain")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="express-retrain",
        description="Réentraîne le modèle s'il y a assez de nouvelles commandes (ADR-0009).",
    )
    parser.add_argument(
        "--watch", action="store_true", help="Vérifier en boucle (planificateur intégré)."
    )
    return parser.parse_args(argv)


def run_once(service: RetrainingService) -> bool:
    """Une vérification. Retourne False en cas d'échec (journalisé, jamais silencieux)."""
    try:
        outcome = service.run()
    except DomainError as error:
        logger.error("Réentraînement impossible : %s", error)
        return False
    if outcome.trained and outcome.new_model is not None:
        logger.info(
            "Nouveau modèle %s : %s", outcome.new_model.model_version, outcome.new_model.metrics
        )
    return True


def main(argv: Sequence[str] | None = None, *, stop: threading.Event | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args(argv)
    try:
        settings = Settings.from_env()
        infrastructure = build_infrastructure(settings)
    except DomainError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1
    service = RetrainingService(
        infrastructure.dataset_source,
        infrastructure.model_repository,
        min_new_orders=settings.retrain_min_new_orders,
    )

    if not args.watch:
        return 0 if run_once(service) else 1

    stop = stop or threading.Event()
    if threading.current_thread() is threading.main_thread():
        # PID 1 d'un conteneur : sans gestionnaire, « docker stop » attendrait 10 s puis tuerait.
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
    interval = settings.retrain_interval_minutes * 60
    logger.info("Planificateur démarré : vérification toutes les %d min", interval // 60)
    while not stop.is_set():
        run_once(service)  # un échec ne tue pas le planificateur : on réessaie au tour suivant
        stop.wait(interval)
    logger.info("Planificateur arrêté.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
