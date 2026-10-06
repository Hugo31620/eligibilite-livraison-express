# ADR-0001 — Où stocker les commandes clients collectées

**Status :** Accepté
**Date :** 06/10/2026

## Contexte

L'endpoint `POST /v1/orders` collecte des commandes (12 variables métier + identifiant) qui
serviront plus tard à la prédiction asynchrone, au batch (séance 5) et au flux temps réel
(séance 6). L'endpoint `GET /v1/orders/{order_id}` doit pouvoir les relire.

Contraintes retenues :

- Chaque commande est **écrite une fois, lue par identifiant** ; jamais modifiée.
- L'identifiant doit être **unique** et la réponse « accepté » (202) ne doit être donnée
  qu'une fois la commande réellement persistée : il faut une écriture **transactionnelle**.
- Le serveur traite plusieurs requêtes en parallèle (pool de threads) : les **écritures
  concurrentes** ne doivent ni se perdre ni se corrompre.
- Environnement de développement : budget faible, exécution locale, **aucun accès aux
  systèmes de production** et **données générées ou anonymisées** uniquement (cours,
  séparation dev → test → prod).
- Volume de développement : quelques milliers de commandes.
- Données de commandes clients : le schéma ne contient volontairement **aucune donnée
  identifiante** (ni nom, ni adresse, ni e-mail) afin de limiter l'impact RGPD.

## Options considérées

| Option | Avantage | Inconvénient |
|---|---|---|
| A. Fichier plat (JSONL / CSV en ajout) | Aucun service, lisible à l'œil | Pas d'unicité garantie, écritures concurrentes à verrouiller à la main, relecture par identifiant en O(n) |
| B. **SQLite** (fichier local) | Intégré à Python (aucune installation), transactions ACID, clé primaire = unicité garantie, index, SQL | Un seul écrivain à la fois, fichier local : non partageable entre plusieurs machines ou conteneurs |
| C. PostgreSQL | Concurrence élevée, partageable entre instances, sauvegardes, service managé disponible dans le cloud | Service à installer et à maintenir (conteneur en local), surdimensionné pour du développement |
| D. Base documentaire (MongoDB…) | Schéma souple | Nos données sont strictement tabulaires et typées : la souplesse n'apporte rien et on perd les contraintes |

## Décision

**Option B (SQLite) pour l'environnement de développement**, derrière le port `OrderStore`
(`src/eligibilite_livraison/abstractions/order_store.py`). L'adaptateur est
`SqliteOrderStore` (`infrastructure/dev/`).

Le code métier ne dépend que de `OrderStore` : passer à l'option C consiste à écrire
`infrastructure/postgres/PostgresOrderStore` et à l'enregistrer dans la fabrique
`infrastructure/factory.py`, sans toucher à l'API ni aux services.

**Évolution probable vers l'option C (PostgreSQL) dès que l'un de ces seuils est franchi :**
plusieurs instances de l'API en parallèle (déploiement séance 2, mise à l'échelle séance 6),
besoin de partager les commandes avec un autre processus (batch, consommateur de flux),
ou exigence de sauvegarde / rétention en test et en production.

## Conséquences

- Le schéma est **explicite** (une colonne par variable, types `INTEGER` / `REAL` / `TEXT`,
  clé primaire sur `order_id`) pour pouvoir réutiliser les commandes collectées en
  entraînement ou en batch sans parser du JSON.
- Un identifiant déjà connu est refusé (`DuplicateOrderError` → HTTP 422 `duplicate_order`).
  Le contrat ne prévoit pas de 409 : on reste dans les codes qu'il déclare.
- Une connexion SQLite est ouverte **par opération** (sûr avec le pool de threads) ; le
  commit est fait à la sortie du bloc, donc le 202 n'est jamais renvoyé avant l'écriture.
- Le fichier `data/orders.db` est ignoré par Git : il ne contient que des données de dev.
- Une **suite de tests de contrat** (`tests/integration/test_order_store.py`) est écrite contre
  le port, pas contre SQLite : tout futur adaptateur (PostgreSQL) devra la passer à l'identique.
- Aucune migration de schéma n'est outillée pour l'instant ; elle devra l'être (Alembic ou
  équivalent) au moment du passage à PostgreSQL.
- Le jour où le seuil est franchi, cette ADR devra être marquée
  « Status : Superseded by ADR-000X » et une nouvelle décision écrite.
