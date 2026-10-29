# Changelog

Toutes les modifications notables de ce projet sont consignées ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet
respecte le [Semantic Versioning](https://semver.org/lang/fr/). La version de
l'application est indépendante de celle du modèle (`MODEL_VERSION`, ADR-0002).

## [Unreleased]

## [1.1.0] - 2026-10-29

### Added

- **Séance 4 — données réelles et orchestration**
  - Intégration des commandes de l'ERP depuis la base analytique **MongoDB** (ADR-0008).
  - `MongoOrderStore` (`save`, `get`, `get_all`) pour les commandes reçues par l'API
    (collection `api_orders`) et `MongoErpDatasetSource` en lecture seule (collection `orders`).
  - Couche anti-corruption `infrastructure/erp/translation.py` : traduction du vocabulaire et
    des unités de l'ERP, rejet et comptage des valeurs inconnues.
  - Environnements `test` et `prod` (`APP_ENV`) et fichiers `docker-compose.test.yml`
    (simulateur ERP fourni dans `erp/`) et `docker-compose.prod.yml` (authentification MongoDB,
    compte applicatif à droits minimaux, secrets dans `.env.prod`).
  - Orchestrateur de réentraînement `express-retrain [--watch]` et service `retrainer`
    (ADR-0009) : nouvelle version mineure publiée, jamais servie automatiquement.
  - `OrderStore.get_all` et `ModelReader.list_versions`.
  - CI : tests de contrat et d'entraînement sur un vrai MongoDB, validation des fichiers compose.

### Changed

- La règle métier d'étiquetage est extraite dans `data/labeling.py`, partagée par le jeu
  synthétique (résultat identique) et la source ERP.
- `express-train` entraîne sur la source de l'environnement : synthétique en dev, ERP en
  test et en prod. `--rows` ne concerne plus que le dev.
- ADR-0001 et ADR-0004 : stockage des commandes en test et en prod remplacé par l'ADR-0008.

### Security

- L'URI MongoDB (mot de passe) n'apparaît jamais dans la représentation des réglages.
- L'application refuse de démarrer si sa collection d'écriture est celle de l'ERP.

## [1.0.3] - 2026-10-29

### Fixed

- Étape `test` de l'image Docker : ruff classait `eligibilite_livraison` en dépendance tierce
  (pas de `src/` dans l'image) et rejetait l'ordre des imports. Paquets internes déclarés via
  `known-first-party`.
- CI : l'action `aquasecurity/trivy-action@0.28.0` n'existe plus ; le scan utilise directement
  l'image officielle `aquasec/trivy`.

## [1.0.2] - 2026-10-29

### Fixed

- Compatibilité pandas 3 : `DatetimeIndex.dayofweek` (déprécié, `Pandas4Warning`) remplacé par
  `day_of_week` dans la génération des données synthétiques. Les tests échouaient sur
  Python 3.11+ où la CI installe pandas 3.

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

[Unreleased]: https://github.com/Hugo31620/eligibilite-livraison-express/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/Hugo31620/eligibilite-livraison-express/compare/v1.0.3...v1.1.0
[1.0.3]: https://github.com/Hugo31620/eligibilite-livraison-express/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/Hugo31620/eligibilite-livraison-express/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/Hugo31620/eligibilite-livraison-express/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Hugo31620/eligibilite-livraison-express/releases/tag/v1.0.0
