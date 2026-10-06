# eligibilite-livraison-express

API qui prédit si une commande peut être **livrée en express dans la journée**.
TP « Industrialisation de l'IA dans le cloud » (YNOV M2 Data & IA) — **Étape 1 : transformer un
notebook en application**.

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
uvicorn eligibilite_livraison.api.app:create_app --factory --reload   # 2. lance l'API
pytest                                        # 3. lance les tests
```

Documentation interactive : <http://localhost:8000/docs>.

Exemple d'appel :

```powershell
$order = @{ hour=14; day_of_week=2; weekend=0; distance_km=3.5; order_value_eur=89.9; weight_kg=2.4;
            stock_available=1; preparation_time_min=18; carrier_capacity=0.85; weather="normal";
            delivery_zone="centre"; customer_type="premium" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/predictions -Body $order -ContentType "application/json"
```

Configuration par variables d'environnement (voir `.env.example`) : `APP_ENV`, `MODEL_VERSION`,
`ARTIFACTS_DIR`, `ORDERS_DB_PATH`, `PREDICTION_THRESHOLD`.

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

Volontairement **non fait** (YAGNI, contrat `x-session` > 1) : déploiement/CI-CD, MLflow,
`/v1/model`, prédiction batch, historique des prédictions, flux temps réel, `/metrics`.
La « mise en file d'attente » de `POST /v1/orders` n'est pas implémentée : la commande est
persistée et acceptée (202) ; la file arrive avec le batch / temps réel (séances 5 et 6).

## Architecture

```text
src/eligibilite_livraison/
├── domain/            # Cœur métier : OrderFeatures, Prediction, erreurs, liste des variables
├── abstractions/      # Ports (ABC) : OrderStore, ModelReader/Writer, DatasetSource
├── infrastructure/
│   ├── dev/           # Adaptateurs locaux : SqliteOrderStore, FileModelRepository
│   └── factory.py     # Choix des adaptateurs selon APP_ENV  (futur : postgres/, ...)
├── data/              # SyntheticDatasetSource, règles qualité + nettoyage
├── ml/                # Pipeline sklearn, métriques, TrainingService
├── services/          # EligibilityPredictor, PredictorProvider, OrderCollectionService
├── api/               # App FastAPI, routes, schémas, gestion des erreurs
├── container.py       # Racine de composition (assemble les briques)
├── config.py          # Settings depuis l'environnement
└── cli.py             # express-train
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
| 55 — model card | `metadata.json` enregistré avec le modèle (la route `/v1/model` viendra en séance 3) |
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

## Tests

`pytest` — 97 tests : validation du contrat de commande, qualité des données, entraînement de
bout en bout, adaptateurs de stockage, API (succès, 404, 422, 503, 500) et **conformité de
l'API générée avec `openapi.yml`** (`tests/api/test_contract.py`, limité aux opérations de la
séance 1). Qualité du code : `ruff check .`
