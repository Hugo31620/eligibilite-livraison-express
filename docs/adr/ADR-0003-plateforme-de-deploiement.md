# ADR-0003 — Sur quelle plateforme déployer l'application

**Status :** Accepté
**Date :** 09/10/2026

## Contexte

L'application est une **API HTTP** (FastAPI) appelée par d'autres systèmes : site marchand,
outil logistique, traitement batch. Ce n'est ni une application mobile (store), ni une
application de bureau, ni un plugin : d'après le cours, elle doit donc tourner sur un
**serveur**, qu'il soit local, on-premise ou dans le cloud (ce choix-là est traité dans
l'ADR-0004).

La question est donc : **sous quelle forme l'application arrive-t-elle sur ce serveur ?**

Contraintes retenues :

- **Même artefact en dev, test et prod.** On veut déployer exactement ce qui a été testé
  (séparation des environnements, séance 1).
- **Dépendances lourdes et sensibles aux versions** : scikit-learn, pandas, numpy. Un modèle
  `joblib` ne se recharge de façon fiable qu'avec la même version de scikit-learn
  (ADR-0002). Sur la machine de développement, Python 3.14 et TensorFlow sont déjà en
  conflit.
- **Charge** : modeste et irrégulière, avec des pics aux heures de commande. Il faut pouvoir
  lancer plusieurs instances, puis revenir à zéro ou presque.
- La stratégie de déploiement (ADR-0005) a besoin de faire **cohabiter deux versions**.
- **Le code ne doit pas être exposé** (règle du cours) : on ne livre ni le dépôt, ni les
  tests, ni le notebook sur le serveur.
- Le prochain cours porte sur la conteneurisation.

## Options considérées

| Option | Avantage | Inconvénient |
|---|---|---|
| A. Code copié sur une VM + `venv` + service système | Simple à comprendre, aucun outil nouveau | Environnement différent sur chaque machine (« ça marche chez moi »), mises à jour manuelles, faire tourner deux versions est pénible, code source présent sur le serveur |
| B. **Image Docker (OCI)** exécutée par un orchestrateur de conteneurs | Artefact unique et immuable de dev à prod, versions figées (Python, scikit-learn), plusieurs versions côte à côte, exécutable partout (poste, serveur, cloud) | Il faut apprendre Docker et gérer un registre d'images |
| C. Fonction serverless (Azure Functions, AWS Lambda) | Paiement à l'appel, zéro serveur à gérer | Démarrage à froid pénalisant avec scikit-learn et pandas (plusieurs secondes), limites de taille de paquet, modèle de programmation propriétaire, s'éloigne du contrat FastAPI |
| D. Kubernetes géré (AKS, EKS, GKE) | Contrôle total, standard de l'industrie | Surdimensionné pour une API et un proxy : coût du plan de contrôle, compétences, maintenance |

## Décision

**Option B : l'application est livrée comme une image Docker**, construite par le
`Dockerfile` du dépôt :

- **Construction en deux étapes** : l'image finale ne contient que le paquet installé.
  Les tests, le notebook, les ADR, `.git` et les secrets sont exclus (`.dockerignore`).
- **Utilisateur non root** (`uid 10001`), système de fichiers en lecture seule et
  capacités Linux supprimées (`docker-compose.yml`).
- **Image identifiée par sa version** (`eligibilite-livraison-express:1.0.0`) puis par le
  hash du commit en CI. On ne déploie jamais `latest`.
- **Port 8000 interne uniquement.** Il n'est accessible qu'au reverse proxy (ADR-0006).
- L'entraînement utilise **la même image** (`express-train`). Le modèle est donc produit
  avec exactement la version de scikit-learn qui le servira.

L'orchestrateur est fixé par l'ADR-0004 (Azure Container Apps). Pour le poste local,
`docker compose` reproduit la même topologie, avec proxy et API.

**Évolution possible vers l'option D** si le nombre de services dépasse ce que
l'orchestrateur choisi gère bien (au-delà d'une dizaine), ou si l'on a besoin de
fonctionnalités Kubernetes natives (opérateurs, GPU). L'image ne change pas : seul
l'orchestrateur change.

## Conséquences

- `docker compose --profile train run --rm trainer` puis `docker compose up -d` lancent
  l'environnement complet en local.
- Un registre d'images devient nécessaire (Azure Container Registry, ADR-0004). L'image y
  est **scannée** pour détecter les vulnérabilités avant le déploiement.
- Le modèle n'est **pas** dans l'image. Il est monté en lecture seule depuis le volume des
  artefacts (ADR-0002). Changer de modèle ne demande donc pas de reconstruire l'image, et
  inversement.
- La version de Python passe de « celle du poste » à `3.12`, figée dans l'image.
- Ni le `Dockerfile` ni `docker-compose.yml` n'ont pu être exécutés dans l'environnement
  de rédaction (registre Docker Hub inaccessible). Ils sont à valider au cours suivant
  (conteneurisation).
