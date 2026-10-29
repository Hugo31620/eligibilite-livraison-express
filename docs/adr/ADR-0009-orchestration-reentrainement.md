# ADR-0009 — Comment orchestrer le réentraînement du modèle

**Status :** Accepté
**Date :** 29/10/2026

## Contexte

Depuis l'ADR-0008, de nouvelles commandes arrivent en continu dans la base analytique
MongoDB. Le modèle doit être réentraîné quand il y a **suffisamment de nouvelles données**,
sans intervention manuelle.

Contraintes retenues :

- l'entraînement est une **exécution** et non une étape de construction de l'application : il
  ne doit pas passer par la CI/CD (séance 4) ;
- une version de modèle publiée est immuable (ADR-0002) : chaque réentraînement produit une
  nouvelle version ;
- la mise en production d'un modèle demande une **validation humaine** (règles de
  l'environnement de production, séance 1) et se fait par bascule Blue/Green (ADR-0005) ;
- sécurité (ADR-0006, ADR-0007) : aucun composant ne doit obtenir plus de droits que
  nécessaire ;
- budget et simplicité : un seul modèle, un seul flux de données, une seule tâche planifiée.

## Options considérées

| Option | Avantage | Inconvénient |
|---|---|---|
| A. CI/CD (GitHub Actions planifié) | Déjà en place | Mélange construction et exécution ; les runners GitHub n'ont pas accès au réseau privé de la base ; les artefacts produits seraient hors de l'environnement |
| B. Apache Airflow (DAG + `DockerOperator`) | Standard du marché : interface, historique, reprises, dépendances entre tâches (ETL → entraînement) | Webserver, scheduler et base de métadonnées à héberger pour une seule tâche ; le `DockerOperator` exige le **socket Docker**, c'est-à-dire les droits root sur l'hôte |
| C. **Service planifié avec l'image de l'application** (`express-retrain --watch`) | Aucun composant de plus ; même image, mêmes tests, mêmes droits minimaux que l'API ; aucun accès au socket Docker | Pas d'interface ni d'historique d'exécution (seulement les logs) ; ne gère pas de dépendances entre plusieurs tâches |
| D. Planificateur du cloud (Azure Container Apps Job en mode *cron*) | Managé, facturé à l'exécution, logs centralisés | Uniquement dans le cloud (ADR-0004) : pas de solution en local |

## Décision

**Séparer la décision de la planification.**

1. **La décision** (« faut-il réentraîner ? ») est une logique métier, donc dans
   l'application et testée : `RetrainingService` (`ml/retraining.py`). Elle lit les
   données, compare le nombre de commandes exploitables à celui du dernier modèle, et ne
   réentraîne qu'au-delà de `RETRAIN_MIN_NEW_ORDERS` nouvelles commandes. La nouvelle
   version est la mineure suivante (`1.0.0` → `1.1.0`).
2. **La planification** est confiée à l'option C en local, en test et en prod sur un serveur
   (`retrainer` dans `docker-compose.test.yml` et `docker-compose.prod.yml`), puis à
   l'option D dans le cloud. Dans les deux cas, elle appelle la même commande
   `express-retrain` : changer d'orchestrateur ne change pas une ligne de code.

**Le nouveau modèle est publié mais pas servi.** L'API continue de servir `MODEL_VERSION`.
Le passage en production se fait après lecture des métriques, en changeant
`MODEL_VERSION` (bascule Blue/Green, ADR-0005).

**Évolution vers l'option B (Airflow)** dès qu'il y aura plusieurs tâches à enchaîner
(par exemple ETL → contrôle qualité → entraînement → évaluation → notification), ou un
besoin d'interface et d'historique pour l'équipe. Le DAG se limitera alors à appeler
`express-retrain`, de préférence par un `KubernetesPodOperator` ou un Container Apps Job
plutôt que par le socket Docker.

## Conséquences

- Seuils réglables sans redéployer : `RETRAIN_MIN_NEW_ORDERS` (500 en prod, 100 en test) et
  `RETRAIN_INTERVAL_MINUTES` (1 440 en prod, soit une fois par jour, et 2 en test pour la
  démonstration).
- Un échec (base injoignable, données insuffisantes, modèle corrompu) est journalisé et
  n'arrête pas le planificateur : il réessaie au tour suivant. En mode simple, le code de
  sortie vaut 1, pour qu'un planificateur externe le détecte.
- Le planificateur s'arrête proprement sur `docker stop` (signal SIGTERM géré).
- Le nombre de versions de modèle croît avec le temps : une politique de rétention
  (garder les N dernières plus la version servie) sera nécessaire, avec l'arrivée du model
  registry annoncé par l'ADR-0002.
- Pas de surveillance de la dérive pour l'instant : le critère reste le volume de nouvelles
  données. Un critère de performance (métriques sur les commandes récentes) le complétera
  quand les vrais statuts de livraison seront disponibles (ADR-0008).
