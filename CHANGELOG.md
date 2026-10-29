# Changelog

Toutes les modifications notables de ce projet sont consignées ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet
respecte le [Semantic Versioning](https://semver.org/lang/fr/). La version de
l'application est indépendante de celle du modèle (`MODEL_VERSION`, ADR-0002).

## [Unreleased]

## [1.0.1] - 2026-10-29

### Fixed

- Le package `src/eligibilite_livraison/data/` (`quality.py`, `synthetic.py`) était exclu de Git
  par la règle `data/` du `.gitignore`, qui visait seulement le dossier de données à la racine :
  la CI et l'image Docker échouaient à l'import. Règles ancrées à la racine (`/data/`,
  `/artifacts/`) et package ajouté au dépôt.
- Tri des imports (ruff I001) et `zip(..., strict=True)` dans `predict_many` (ruff B905).

## [1.0.0] - 2026-10-26

Première version publiée : l'application est prête à être livrée sous forme d'image Docker.

### Added

- **Séance 3 — CI/CD et collaboration**
  - Organisation GitFlow (`main`, `develop`, `feature/*`, `release/*`, `hotfix/*`).
  - `CONTRIBUTING.md`, `LICENSE` (MIT), `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`,
    modèles d'issues et de Pull Request.
  - Dockerfile multi-stage : étape `test` (pytest + ruff dans l'image) et étape `prod` minimale.
  - Workflow `ci.yml` : lint, tests sur Python 3.10 à 3.13, audit des dépendances, construction
    et test de l'image, scan de vulnérabilités de l'image.
  - Workflow `release.yml` : construction et publication de l'image sur `ghcr.io` à chaque tag
    `vX.Y.Z`.
- **Séance 2 — sécurité et déploiement**
  - Clés d'API nominatives, hachées et expirantes, rôles `guest` / `user` / `admin`,
    outil `express-apikey`.
  - `GET /v1/model` (model card) et `POST /v1/predictions/batch`.
  - Image Docker non-root, reverse proxy nginx (seul port exposé, limitation de débit).
  - ADR 0003 à 0007 : plateforme, cloud, stratégie Blue/Green, sécurité des entrées/sorties
    et de l'accès aux données.
- **Séance 1 — du notebook à l'application**
  - API FastAPI conforme à `openapi.yml` : `/health`, `/health/ready`, `/v1/predictions`,
    `/v1/orders`.
  - Commande `express-train`, artefacts de modèle versionnés et immuables.
  - Architecture en ports et adaptateurs, ADR 0001 et 0002.

### Security

- Empreinte SHA-256 du modèle vérifiée avant `joblib.load`.
- Aucun secret ni fichier `.env` dans l'image Docker ; conteneur en lecture seule sans
  capacités Linux.

[Unreleased]: https://github.com/Hugo31620/eligibilite-livraison-express/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/Hugo31620/eligibilite-livraison-express/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Hugo31620/eligibilite-livraison-express/releases/tag/v1.0.0
