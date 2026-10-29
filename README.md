# eligibilite-livraison-express

[![CI](https://github.com/Hugo31620/eligibilite-livraison-express/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Hugo31620/eligibilite-livraison-express/actions/workflows/ci.yml)
[![Release](https://github.com/Hugo31620/eligibilite-livraison-express/actions/workflows/release.yml/badge.svg)](https://github.com/Hugo31620/eligibilite-livraison-express/actions/workflows/release.yml)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

API qui prédit si une commande peut être **livrée en express dans la journée**.
TP « Industrialisation de l'IA dans le cloud » (YNOV M2 Data & IA) :

- **Séance 1** : transformer le notebook en application.
- **Séance 2** : finir l'application, sécuriser l'accès par rôles et rédiger les ADR de
  déploiement.
- **Séance 3** : CI/CD (GitHub Actions), GitFlow, image Docker multi-stage publiée sur
  `ghcr.io`, fichiers de collaboration.
- **Séance 4** : données réelles de l'ERP via MongoDB, environnements Docker de test et de
  prod, orchestration du réentraînement.

Le notebook d'origine (`project_test_v1_final_final2.ipynb`) génère des données, les nettoie,
entraîne une régression logistique et prédit. Ici, chaque responsabilité a son module, son
test, et l'ensemble est exposé en HTTP conformément au contrat [`openapi.yml`](openapi.yml).

## Démarrage rapide

Prérequis : Python 3.10+.

```powershell
# Windows PowerShell                          # Linux / macOS
python -m venv .venv                          # python3 -m venv .venv
.venv\Scripts\Activate.ps1                    # source .venv/bin/activate
pip install -e ".[dev]"

express-train                                 # 1. entraîne et enregistre artifacts/1.0.0/
express-apikey create --name hugo --role admin --days 30   # 2. crée une clé (affichée UNE fois)
uvicorn eligibilite_livraison.api.app:create_app --factory --reload   # 3. lance l'API
pytest                                        # 4. lance les tests
```

Documentation interactive (en dev uniquement) : <http://localhost:8000/docs>. Pour essayer les
routes protégées depuis cette page, cliquer sur **Authorize** et coller la clé.

Exemple d'appel :

```powershell
$headers = @{ "X-API-Key" = "sk_dev_..." }   # la clé affichée par express-apikey
$order = @{ hour=14; day_of_week=2; weekend=0; distance_km=3.5; order_value_eur=89.9; weight_kg=2.4;
            stock_available=1; preparation_time_min=18; carrier_capacity=0.85; weather="normal";
            delivery_zone="centre"; customer_type="premium" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/predictions -Headers $headers -Body $order -ContentType "application/json"
```

Configuration par variables d'environnement (voir `.env.example`) : `APP_ENV`, `MODEL_VERSION`,
`ARTIFACTS_DIR`, `ORDERS_DB_PATH`, `PREDICTION_THRESHOLD`, `API_KEYS_FILE`, `EXPOSE_API_DOCS`.

### Image publiée (sans cloner le dépôt)

Chaque version taggée est publiée sur le GitHub Container Registry :

```bash
docker pull ghcr.io/hugo31620/eligibilite-livraison-express:1.1.1
```

### Avec Docker (topologie de production, ADR-0003 et ADR-0006)

```powershell
express-apikey create --name hugo --role user --days 30   # crée secrets/api_keys.json
docker compose --profile train run --rm trainer          # entraîne le modèle dans le volume
docker compose up -d --build                             # proxy nginx (:8080) + API (interne)
curl http://localhost:8080/health
```

Seul le port **8080** du proxy est ouvert. L'API (8000) n'est joignable que depuis le
réseau interne. `/docs` et `/openapi.json` n'existent pas.

### Environnement de test : données de l'ERP (ADR-0008, ADR-0009)

MongoDB (base analytique), le simulateur ERP fourni (`erp/`), l'API, le proxy et
l'orchestrateur de réentraînement :

```powershell
express-apikey create --name testeur --role admin --days 7     # crée secrets/api_keys.json
docker compose -f docker-compose.test.yml up -d --build        # tout démarre ; proxy sur :8081
docker compose -f docker-compose.test.yml logs erp-simulator   # attendre « Historique partagé 2023+ »
docker compose -f docker-compose.test.yml run --rm trainer     # entraîne le modèle 1.0.0 sur l'ERP
curl.exe http://localhost:8081/health/ready                    # {"status":"ready", ...}
docker compose -f docker-compose.test.yml logs -f retrainer    # publie 1.1.0, 1.2.0... au fil des lots
docker compose -f docker-compose.test.yml down -v              # tout supprimer
```

### Environnement de production

Image épinglée, MongoDB avec authentification et compte applicatif à droits minimaux
(`deploy/mongo/init-app-user.js`), aucun port publié hormis le proxy, secrets dans
`.env.prod` (hors Git) :

```powershell
Copy-Item .env.prod.example .env.prod                           # puis remplir les secrets
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm trainer
```

En prod, la collection `orders` est alimentée par l'ETL de l'entreprise, pas par le simulateur.

## Sécurité et rôles (ADR-0006, ADR-0007)

| Route | Public | `guest` | `user` | `admin` |
|---|:-:|:-:|:-:|:-:|
| `GET /health`, `GET /health/ready` | ✅ | ✅ | ✅ | ✅ |
| `GET /v1/model` | ❌ | ✅ | ✅ | ✅ |
| `POST /v1/predictions`, `POST /v1/predictions/batch`, `POST /v1/orders` | ❌ | ❌ | ✅ | ✅ |
| `GET /v1/orders/{id}` (données clients) | ❌ | ❌ | ❌ | ✅ |

- Les clés sont envoyées dans l'en-tête `X-API-Key`. Elles expirent en **90 jours au
  plus**.
- On ne stocke que leur **empreinte SHA-256**, dans `secrets/` (hors Git) ou dans Key Vault
  en cloud, jamais dans `.env`.
- Gestion : `express-apikey create | list | revoke`. La révocation prend effet sans
  redémarrage.

## Ce qui est livré (séance 1)

| Élément à industrialiser (dernière cellule du notebook) | Solution technique |
|---|---|
| Collecte de données | `POST /v1/orders` + `GET /v1/orders/{id}` → port `OrderStore`, adaptateur SQLite ([ADR-0001](docs/adr/ADR-0001-stockage-commandes-clients.md)) |
| Exposition d'une fonction de prédiction | `POST /v1/predictions` (FastAPI), erreurs au format `Error` du contrat |
| Entraînement du modèle | Commande `express-train` → `TrainingService` |
| Prédiction à l'aide du modèle | `EligibilityPredictor` + `PredictorProvider` (chargement paresseux du modèle versionné) |
| Environnement (dev → test → prod) | `APP_ENV` + `infrastructure/<env>/` + `infrastructure/factory.py` (dev implémenté) |
| Sauvegarde du modèle | Dossier versionné et immuable `artifacts/<version>/` ([ADR-0002](docs/adr/ADR-0002-stockage-artefacts-modele.md)) — sera revue en séance 3 |
| Sondes | `GET /health` (vivacité, sans dépendance) et `GET /health/ready` (modèle + stockage) |

## Ce qui est livré (séance 2)

| Élément | Solution technique |
|---|---|
| Fin du portage du notebook | `GET /v1/model` (model card, cellule 55), `POST /v1/predictions/batch` (prédiction vectorisée, cellule 46) |
| Accès par rôles `admin` / `user` / `guest` | Clés d'API nominatives, hachées, avec expiration, outil `express-apikey` ([ADR-0007](docs/adr/ADR-0007-securiser-acces-aux-donnees.md)) |
| Blocage des ports, code non exposé | Reverse proxy nginx seul port ouvert, API interne, `/docs` coupé en prod, image sans sources annexes ([ADR-0006](docs/adr/ADR-0006-securiser-entrees-sorties.md)) |
| Limitation de débit | nginx : 10 req/s par IP, rafale de 20, corps de 1 Mo maximum |
| Intégrité du modèle | Empreinte SHA-256 vérifiée **avant** `joblib.load` |
| Plateforme de déploiement | Image Docker non-root ([ADR-0003](docs/adr/ADR-0003-plateforme-de-deploiement.md)) |
| Cloud / on-premise / local | Local en dev, Azure (France Central) en test et prod ([ADR-0004](docs/adr/ADR-0004-cloud-et-services.md)) |
| Stratégie de déploiement | Blue/Green par révisions Azure Container Apps ([ADR-0005](docs/adr/ADR-0005-strategie-de-deploiement.md)) |

## Ce qui est livré (séance 3)

| Élément | Solution technique |
|---|---|
| Projet sur GitHub, GitFlow | Branches `main` (production, taggée), `develop`, `feature/*`, `release/*`, `hotfix/*` ([CONTRIBUTING](CONTRIBUTING.md#organisation-des-branches-gitflow)) |
| Versions et journal | Semantic Versioning (`v1.0.0`) et [CHANGELOG](CHANGELOG.md) au format Keep a Changelog |
| Collaboration | [CONTRIBUTING](CONTRIBUTING.md), [LICENSE](LICENSE) (MIT), [SECURITY](SECURITY.md), [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md), modèles d'issues et de PR |
| Image Docker optimisée | Build multi-stage : `build` (roues) → `test` (pytest + ruff dans l'image) → `prod` (slim, sans tests, outils, `.env`, doc ni README) |
| Image Docker sécurisée | Utilisateur non-root (uid 10001), secrets passés à l'exécution, seul le port 8000 exposé (vers le proxy) |
| Tests automatiques | [`ci.yml`](.github/workflows/ci.yml) sur chaque push / PR : ruff, pytest sur Python 3.10 → 3.13, `pip-audit`, construction et exécution de l'étape `test`, scan Trivy de l'image `prod` |
| Image à chaque release | [`release.yml`](.github/workflows/release.yml) : tag `vX.Y.Z` → tests dans l'image → publication `ghcr.io/hugo31620/eligibilite-livraison-express:X.Y.Z` (+ `X.Y`, `latest`) |

## Ce qui est livré (séance 4)

| Élément | Solution technique |
|---|---|
| Choix de la base | **MongoDB** (base analytique) plutôt que PostgreSQL (production de l'ERP, partagée avec une application critique, sans administrateur) ([ADR-0008](docs/adr/ADR-0008-source-donnees-erp-mongodb.md)) |
| Implémentation de `OrderRepository` | `MongoOrderStore` (`save`, `get`, `get_all`) pour les commandes reçues par l'API, dans la collection `api_orders` ; `MongoErpDatasetSource` lit la collection `orders` de l'ERP **sans jamais l'écrire** |
| Validation des données depuis l'application | Couche anti-corruption `infrastructure/erp/translation.py` : vocabulaire et unités de l'ERP traduits vers ceux du domaine, valeurs inconnues **rejetées et comptées**, puis nettoyage et validation habituels |
| Cible absente de l'ERP | Étiquetage par la règle métier du notebook (`data/labeling.py`), limite documentée dans l'ADR-0008 |
| Tests sur les nouvelles données | Traduction, source, entraînement puis prédiction sur des commandes au format ERP ; contrat `OrderStore` rejoué sur SQLite, `mongomock` et un **vrai MongoDB** (service `mongodb` de la CI) |
| docker-compose de test et de prod | [`docker-compose.test.yml`](docker-compose.test.yml) (simulateur ERP, MongoDB ouvert en local) et [`docker-compose.prod.yml`](docker-compose.prod.yml) (authentification, moindre privilège, secrets, image épinglée) |
| Orchestrateur de réentraînement | `express-retrain --watch` (service `retrainer`) : réentraîne au-delà de `RETRAIN_MIN_NEW_ORDERS` nouvelles commandes et publie la version mineure suivante **sans la servir** ([ADR-0009](docs/adr/ADR-0009-orchestration-reentrainement.md)) |

Volontairement **non fait** (YAGNI) : déploiement continu vers Azure, Airflow (une seule tâche,
voir ADR-0009), `BlobModelRepository`, MLflow, historique des prédictions, flux temps réel, `/metrics`.
La « mise en file d'attente » de `POST /v1/orders` n'est pas implémentée : la commande est
persistée et acceptée (202) ; la file arrive avec le batch / temps réel (séances 5 et 6).

## Architecture

```text
src/eligibilite_livraison/
├── domain/            # Cœur métier : OrderFeatures, Prediction, erreurs, liste des variables
├── abstractions/      # Ports (ABC) : OrderStore, ModelReader/Writer, DatasetSource, ApiKeyStore
├── infrastructure/
│   ├── dev/           # Adaptateurs locaux : SqliteOrderStore, FileModelRepository, JsonFileApiKeyStore
│   ├── erp/           # Couche anti-corruption : format de l'ERP → vocabulaire du domaine
│   ├── mongo/         # Test / prod : MongoOrderStore, MongoErpDatasetSource
│   └── factory.py     # Choix des adaptateurs selon APP_ENV (dev → SQLite, test / prod → MongoDB)
├── data/              # SyntheticDatasetSource, étiquetage métier, règles qualité + nettoyage
├── ml/                # Pipeline sklearn, métriques, TrainingService, RetrainingService
├── services/          # EligibilityPredictor, PredictorProvider, OrderCollectionService,
│                      # AuthenticationService, model card
├── api/               # App FastAPI, routes, schémas, erreurs, contrôle d'accès (security.py)
├── container.py       # Racine de composition (assemble les briques)
├── config.py          # Settings depuis l'environnement
├── cli.py             # express-train
├── retrain_cli.py     # express-retrain [--watch]  (orchestrateur, ADR-0009)
└── apikey_cli.py      # express-apikey create / list / revoke
```

Sens des dépendances : `api → services → abstractions ← infrastructure`, et tout le monde
connaît `domain`. L'API et les services ne savent jamais qu'il y a SQLite ou un dossier local.

### Du notebook au code

| Cellules du notebook | Devient |
|---|---|
| 8 — génération des données | `data/synthetic.py` (`SyntheticDatasetSource`) |
| 14, 18 — contrôle qualité, nettoyage | `data/quality.py` |
| 20 — variables | `domain/features.py` (unique source de vérité) |
| 22, 24, 26, 28 — split, pipeline, entraînement, métriques | `ml/training.py`, `ml/pipeline.py`, `ml/metrics.py` |
| 34, 39 — prédiction et ses tests | `services/predictor.py` + `tests/` |
| 41, 43 — sauvegarde / rechargement | `infrastructure/dev/file_model_repository.py` |
| 46 — prédiction batch | `EligibilityPredictor.predict_many` + `POST /v1/predictions/batch` |
| 55 — model card | `services/model_card.py` + `GET /v1/model` |
| 12, 30, 52, 53 — graphiques, exploration | Restent dans le notebook : c'est de l'expérimentation, pas de la production |

## Principes appliqués

| Principe | Où le voir |
|---|---|
| **S** — une raison de changer | Une classe = un rôle : `TrainingService` orchestre, `compute_metrics` mesure, `FileModelRepository` stocke, `EligibilityPredictor` prédit. Les routes ne contiennent aucune logique. |
| **O** — ouvert / fermé | Nouvel environnement ou stockage = nouvelle classe + une ligne dans `factory.py`, sans modifier l'existant. |
| **L** — substitution | Tout `OrderStore` / `ModelRepository` est interchangeable : `tests/integration/test_order_store.py` est un test de contrat rejoué sur chaque adaptateur. |
| **I** — ségrégation des interfaces | `ModelReader` (API) et `ModelWriter` (entraînement) sont séparés : l'API ne peut pas écrire de modèle. |
| **D** — inversion des dépendances | Services et API dépendent des ABC de `abstractions/` ; `container.py` est le seul endroit qui connaît les classes concrètes. |
| **DRY** | Variables définies une fois (`features.py`) ; règles qualité déclarées une fois (`COLUMN_RULES`) et partagées par validation et nettoyage ; contraintes de la commande portées par un seul modèle Pydantic, utilisé par l'API, le stockage et le modèle. |
| **YAGNI** | Rien qui ne soit demandé par le contrat de la séance 1 (voir « non fait »). Pas de framework d'injection, pas d'ORM, pas de couche de cache. |
| **Clean Code** | Noms parlants, fonctions courtes, pas de variable globale mutable, erreurs typées avec code stable, pas de `print` dans le code métier (logging), types partout, `ruff` propre. |
| **Design patterns** | *Repository* (`OrderStore`, `ModelRepository`), *Strategy* (`DatasetSource`), *Factory* (`build_infrastructure`, `create_app`), *Dependency Injection* (constructeurs + `Depends`), *Adapter* (`infrastructure/`), *Provider* à chargement paresseux (`PredictorProvider`). |

## Choix à connaître

- **Doublon d'identifiant** sur `POST /v1/orders` → 422 `duplicate_order` (le contrat ne
  déclare pas de 409).
- **Version du modèle explicite** (`X.Y.Z`, jamais « latest ») et **immuable** : réentraîner sans
  changer de version est refusé volontairement. `express-train --model-version 1.1.0`, puis
  `MODEL_VERSION=1.1.0`.
- **Le modèle manque ?** L'API démarre quand même : `/health` = 200, `/health/ready` et
  `/v1/predictions` = 503. Dès que `express-train` a tourné, elle devient disponible sans
  redémarrage.
- **Nettoyage** : appliqué avec les mêmes règles que la validation (le notebook oubliait la
  borne de `hour`), donc `validate(clean(x))` passe toujours.
- Les résultats diffèrent légèrement du notebook (accuracy ≈ 0,77 contre 0,7525 ; vérifié : en rejouant ce flux, on retrouve exactement les métriques du notebook) car le notebook
  nettoyait un jeu auquel il avait ajouté un doublon, ce qui changeait l'ordre des lignes avant
  le découpage entraînement/test.

## Décisions d'architecture (ADR)

| ADR | Décision |
|---|---|
| [0001](docs/adr/ADR-0001-stockage-commandes-clients.md) | Commandes dans SQLite en dev, puis PostgreSQL |
| [0002](docs/adr/ADR-0002-stockage-artefacts-modele.md) | Artefacts du modèle dans un dossier versionné et immuable |
| [0003](docs/adr/ADR-0003-plateforme-de-deploiement.md) | Plateforme : image Docker |
| [0004](docs/adr/ADR-0004-cloud-et-services.md) | Local en dev, cloud Azure en test et prod, avec la liste des services |
| [0005](docs/adr/ADR-0005-strategie-de-deploiement.md) | Stratégie Blue/Green, rollback instantané |
| [0006](docs/adr/ADR-0006-securiser-entrees-sorties.md) | Sécurité des entrées et sorties : défense en profondeur |
| [0007](docs/adr/ADR-0007-securiser-acces-aux-donnees.md) | Accès à la donnée : rôles et clés d'API |
| [0008](docs/adr/ADR-0008-source-donnees-erp-mongodb.md) | Données de l'ERP depuis MongoDB (base analytique) plutôt que PostgreSQL (production) |
| [0009](docs/adr/ADR-0009-orchestration-reentrainement.md) | Réentraînement planifié par `express-retrain`, mise en service manuelle |

## Tests

`pytest` lance 229 tests :

- validation du contrat de commande et qualité des données ;
- entraînement de bout en bout et adaptateurs de stockage ;
- intégrité du modèle (artefact altéré refusé) ;
- API : succès, 401, 403, 404, 422, 503 et 500 ;
- matrice complète **rôle × route** ;
- model card et batch ;
- **conformité de l'API générée avec `openapi.yml`** (`tests/api/test_contract.py`) ;
- traduction des données ERP, entraînement et prédiction sur ces données, réentraînement ;
- contrat `OrderStore` sur SQLite, MongoDB en mémoire (`mongomock`) et vrai MongoDB.

Les tests sur un vrai MongoDB ne tournent que si `MONGO_TEST_URI` est défini (CI, ou en local
avec le compose de test : `$env:MONGO_TEST_URI="mongodb://localhost:27018"; pytest`).

Qualité du code : `ruff check .`

Les mêmes vérifications tournent dans l'image : `docker build --target test .`

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md) (branches, commits, versions, PR) et
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Vulnérabilité : [SECURITY.md](SECURITY.md).

## Licence

[MIT](LICENSE) © 2026 Hugo31620
