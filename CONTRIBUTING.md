# Contribuer à eligibilite-livraison-express

Merci de prendre le temps de contribuer. Ce document explique comment proposer un
changement pour qu'il soit relu et intégré rapidement.

## Avant de commencer

- Lisez le [README](README.md) (architecture, principes appliqués) et les
  [ADR](docs/adr/) : toute décision structurante passe par une nouvelle ADR.
- Respectez le [code de conduite](CODE_OF_CONDUCT.md).
- Une faille de sécurité ne se signale **jamais** dans une issue publique : voir
  [SECURITY.md](SECURITY.md).

## Signaler un bug ou proposer une évolution

Ouvrez une [issue](../../issues/new/choose) avec le modèle adapté :

- **Bug** : version concernée (`GET /v1/model` ou tag Git), étapes pour reproduire,
  résultat attendu, résultat obtenu, logs utiles (sans clé d'API ni donnée client).
- **Évolution** : besoin métier, solution envisagée, alternatives écartées.

Vérifiez d'abord qu'une issue équivalente n'existe pas déjà.

## Organisation des branches (GitFlow)

| Branche | Rôle | Créée depuis | Fusionnée dans |
|---|---|---|---|
| `main` | Code en production, chaque commit est taggé `vX.Y.Z` | — | — |
| `develop` | Intégration de la prochaine version | `main` | `release/*` |
| `feature/<sujet>` | Une fonctionnalité ou un chantier | `develop` | `develop` |
| `release/X.Y.Z` | Stabilisation d'une version (corrections, CHANGELOG) | `develop` | `main` **et** `develop` |
| `hotfix/X.Y.Z` | Correction urgente en production | `main` | `main` **et** `develop` |

`main` et `develop` sont protégées : on n'y pousse jamais directement, tout passe par une
Pull Request relue avec une CI verte.

```bash
git switch develop && git pull
git switch -c feature/historique-predictions
# ... commits ...
git push -u origin feature/historique-predictions   # puis ouvrir la PR vers develop
```

## Messages de commit

Format [Conventional Commits](https://www.conventionalcommits.org/fr/) :

```text
<type>(<portée optionnelle>): <résumé à l'impératif, en minuscules>

<corps optionnel : le pourquoi, pas le comment>
```

Types : `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`.
Un changement non rétrocompatible ajoute `!` (`feat!: ...`) et une ligne
`BREAKING CHANGE: ...` dans le corps.

## Versions et journal des modifications

- Numérotation [Semantic Versioning](https://semver.org/lang/fr/) `MAJEUR.MINEUR.CORRECTIF` :
  - **MAJEUR** : rupture du contrat `openapi.yml` (champ supprimé, route renommée…) ;
  - **MINEUR** : ajout rétrocompatible (nouvelle route, champ optionnel) ;
  - **CORRECTIF** : correction sans changement de contrat.
- La version de l'**application** (`pyproject.toml`, `__init__.py`, `openapi.yml`) est
  indépendante de celle du **modèle** (`MODEL_VERSION`, ADR-0002).
- Chaque PR met à jour la section `[Unreleased]` de [CHANGELOG.md](CHANGELOG.md) au format
  [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## Mettre en place l'environnement

```bash
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Règles de code

- Python ≥ 3.10, typé, respect de l'architecture : `api → services → abstractions ← infrastructure`.
  Une nouvelle technologie de stockage = un nouvel adaptateur dans `infrastructure/<env>/`,
  jamais un `if` dans un service.
- Aucun secret, aucune donnée réelle, aucun artefact de modèle dans Git.
- Toute fonctionnalité ou correction arrive avec ses tests.

Avant d'ouvrir la PR, ces commandes doivent passer (la CI les rejoue) :

```bash
ruff check .
ruff format --check .   # facultatif tant que le dépôt n'est pas entièrement formaté
pytest
docker build --target test .
```

## Pull Requests

1. Une PR = un sujet. Gardez-la petite (idéalement moins de 400 lignes).
2. Cible : `develop` (ou `main` pour un `hotfix/*`).
3. Remplissez le modèle de PR : contexte, changements, tests, issue liée (`Closes #12`).
4. CI verte et une relecture approuvée obligatoires avant fusion.
5. Fusion en *squash* pour les `feature/*`, en *merge commit* pour `release/*` et `hotfix/*`
   (l'historique de version reste lisible sur `main`).

## Publier une version (mainteneurs)

```bash
git switch -c release/1.1.0 develop
# mettre la version à jour (pyproject.toml, __init__.py, openapi.yml) et le CHANGELOG
git switch main && git merge --no-ff release/1.1.0
git tag -a v1.1.0 -m "v1.1.0" && git push origin main v1.1.0
git switch develop && git merge --no-ff release/1.1.0 && git push
```

Le tag `v1.1.0` déclenche la construction et la publication de l'image Docker
`ghcr.io/hugo31620/eligibilite-livraison-express:1.1.0` (workflow `release.yml`).
