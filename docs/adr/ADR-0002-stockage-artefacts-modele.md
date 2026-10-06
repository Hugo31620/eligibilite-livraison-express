# ADR-0002 — Où stocker les artefacts du modèle de Machine Learning

**Status :** Accepté
**Date :** 06/10/2026

## Contexte

L'API doit pouvoir **recharger un modèle au démarrage sans réentraîner** à chaque
redéploiement. Le modèle est un pipeline scikit-learn (prétraitement + régression
logistique) sérialisé avec `joblib` : quelques Ko à quelques Mo, **écrit rarement** (à chaque
entraînement) et **lu très souvent** (chaque démarrage de l'API).

Contraintes retenues :

- Chaque prédiction renvoie un `model_version` : on doit toujours savoir **quel modèle** a
  répondu, et pouvoir **revenir** à la version précédente.
- Les métriques, les variables attendues et la date d'entraînement doivent voyager **avec** le
  modèle (traçabilité, future route `GET /v1/model` de la séance 3).
- Un fichier `joblib` est un *pickle* : le charger exécute du code. Il ne doit venir que d'une
  source **de confiance**, et il dépend de la version de scikit-learn qui l'a produit.
- Une API qui démarre avec un fichier à moitié écrit ou corrompu doit **échouer proprement**
  (503 / sonde de disponibilité rouge), pas répondre n'importe quoi.

## Options considérées

| Option | Avantage | Inconvénient |
|---|---|---|
| A. **Répertoire local versionné** (`artifacts/<version>/`) | Aucun service à installer, versions explicites et immuables, parfait pour du développement | Pas de partage entre machines, pas de gestion des droits ni de statuts (staging / production) |
| B. Système de fichiers réseau / volume partagé | Partage simple entre plusieurs machines | Accès concurrents pénibles, versionnage à la main, dépendance à l'infrastructure |
| C. Stockage objet (S3, Azure Blob, GCS) avec versionnage | Durable, partageable, peu cher, droits fins | Dépendance cloud et identifiants à gérer dès le développement |
| D. Model Registry (MLflow) | Versionnage natif, statuts, lien avec les métriques et les runs d'entraînement | Service supplémentaire à maintenir, plus lourd que le besoin actuel |

## Décision

**Option A (répertoire local versionné)** derrière les ports `ModelReader` / `ModelWriter`
(`abstractions/model_repository.py`) ; l'adaptateur est `FileModelRepository`
(`infrastructure/dev/`).

Disposition :

```text
artifacts/
└── 1.0.0/
    ├── model.joblib     # pipeline scikit-learn complet (prétraitement + classifieur)
    └── metadata.json    # version, date, version de scikit-learn, variables, métriques, tailles des jeux
```

Règles :

1. **La version est explicite** : l'API sert `MODEL_VERSION` (jamais « latest »), au format `X.Y.Z`.
2. **Une version publiée est immuable** : republier `1.0.0` est refusé (`ModelAlreadyExistsError`).
   Un nouvel entraînement = un nouveau numéro de version.
3. Écriture dans un dossier temporaire puis renommage : on ne lit jamais un artefact à moitié écrit.
4. Lecture et écriture sont **deux ports distincts** : l'API n'a accès qu'à la lecture, seul
   l'entraînement écrit.

**Évolution probable vers l'option D (Model Registry MLflow), éventuellement adossée à
l'option C pour le stockage physique, dès que** : l'API et l'entraînement tournent sur des
machines différentes (déploiement séance 2, sauvegarde du modèle séance 3), ou qu'il faut des
statuts (staging → production) et la comparaison de runs (MLflow, séance 4).

## Conséquences

- Chaque version du modèle est identifiée explicitement ; le retour arrière revient à changer
  la variable `MODEL_VERSION` et à redémarrer l'API.
- Les artefacts ne sont **pas versionnés dans Git** (`artifacts/` dans `.gitignore`) : ils sont
  produits par `express-train`. Il faudra décider en séance 2/3 comment ils arrivent dans
  l'environnement de test puis de production (image, volume ou registre).
- La version de scikit-learn est enregistrée dans `metadata.json` : un modèle chargé avec une
  autre version est un risque connu du format *pickle*, à traiter par un entraînement dans le
  même environnement que le service.
- Aucune vérification d'intégrité (empreinte) n'est faite à ce stade : à ajouter avec la
  sécurisation de la chaîne de déploiement (séance 2), car charger un *pickle* altéré exécute
  du code arbitraire.
- La non-régression vis-à-vis du notebook est protégée par un test (`test_training_service.py`)
  qui vérifie que l'accuracy et le ROC-AUC restent au niveau du notebook.
- Le jour où le seuil est franchi, cette ADR devra être marquée
  « Status : Superseded by ADR-000X » et une nouvelle décision écrite. Elle sera de toute façon
  relue en séance 3 (sauvegarde du modèle).
