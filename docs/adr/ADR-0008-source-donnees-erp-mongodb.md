# ADR-0008 — Depuis quelle base intégrer les données de l'ERP : PostgreSQL ou MongoDB

**Status :** Accepté
**Date :** 29/10/2026
**Remplace en partie :** ADR-0001 et ADR-0004 (stockage des commandes en test et en prod)

## Contexte

Jusqu'ici, le modèle était entraîné sur un jeu synthétique. Il doit maintenant l'être sur les
commandes réelles de l'ERP (« ERP Pro 2015 »), accessibles par deux bases :

| | PostgreSQL | MongoDB |
|---|---|---|
| Rôle | **Base de production** de l'ERP, échange bilatéral en temps réel | **Base analytique**, alimentée à sens unique par un ETL |
| Historique | Depuis 2015 | Depuis 2023 seulement (l'historique antérieur n'a pas été copié) |
| Schéma | Modifié en 2017 et 2023 ; `weekend` vide avant juillet 2015, `preparation_time_min` vide avant juillet 2017 | Documents homogènes : toutes les colonnes renseignées |
| Utilisateurs | Une **autre application critique** pour l'entreprise | Créée pour les Data Analysts, justement pour qu'ils ne cassent plus la production |
| Maintenance | **Plus d'administrateur** depuis 2023 (démission, non remplacé) | Un alternant, bientôt en fin de contrat |

Contraintes du projet :

- l'application **lit** les commandes pour entraîner, et **écrit** les commandes reçues par
  `POST /v1/orders` ;
- un entraînement fait des lectures massives (toute la table) à une fréquence régulière
  (orchestrateur, séance 4) ;
- règle des environnements (séance 1) : on ne touche pas à un système de production sans
  validation, et un incident dans le projet Data ne doit jamais impacter un autre service.

## Options considérées

| Option | Avantage | Inconvénient |
|---|---|---|
| A. **PostgreSQL** (production) | Historique complet depuis 2015 ; données en temps réel ; SQL et contraintes de schéma | Lectures massives sur une base **partagée avec une application critique** : risque de ralentissement ou de verrou ; aucun administrateur pour accorder un compte en lecture seule, surveiller la charge ou réagir à un incident ; schéma ayant migré deux fois, avec des valeurs manquantes à gérer avant 2017 ; un bug d'écriture côté projet Data toucherait directement l'ERP |
| B. **MongoDB** (analytique) | **Conçue pour les usages Data** : une requête lourde ou une erreur ne peut pas impacter la production ; flux à sens unique (une modification côté Data ne remonte jamais dans l'ERP) ; documents complets, sans valeur manquante due aux migrations ; connexion simple (`pymongo`) | Historique limité à 2023 ; dépend de la fraîcheur de l'ETL ; base maintenue par un alternant sur le départ ; pas de schéma imposé, la qualité doit être contrôlée par l'application |
| C. Réplica en lecture de PostgreSQL | Historique complet sans charger la production | N'existe pas : il faudrait le créer et l'administrer, alors que personne n'administre déjà la base source |

## Décision

**Option B : MongoDB, base analytique.** Le principe qui tranche est l'isolement : un
projet Data ne doit jamais pouvoir dégrader la production. L'option A ferait porter à une
application critique, sans administrateur, la charge et le risque de notre projet.

L'historique limité à 2023 est acceptable : près de trois ans de commandes suffisent à un
modèle de régression logistique, et ce sont les données les plus représentatives de
l'activité actuelle (le schéma actuel date de 2023). Si un besoin d'historique profond
apparaît, la bonne réponse sera de **rejouer l'historique PostgreSQL dans la base analytique
par l'ETL** (ou de créer un réplica, option C), pas de brancher l'application sur la
production.

### Mise en œuvre

- `MongoErpDatasetSource` (`infrastructure/mongo/`) **lit seulement** la collection `orders`
  alimentée par l'ETL (aucune écriture possible : la source n'appelle que `find`).
- Les commandes reçues par l'API sont écrites dans une **collection propre à l'application**,
  `api_orders` (`MongoOrderStore`), jamais dans `orders`. La configuration refuse au
  démarrage que les deux noms soient identiques.
- Le dev reste sur SQLite et le jeu synthétique (aucun accès aux données réelles en dev) ;
  `test` et `prod` utilisent MongoDB (`APP_ENV`, `infrastructure/factory.py`).

### Les données de l'ERP ne parlent pas la langue du domaine

Constat en intégrant la collection : le vocabulaire et les unités de l'ERP diffèrent de
ceux du modèle et du contrat `openapi.yml`. Plutôt que de modifier le contrat (ce serait une
rupture, donc une version majeure), une **couche anti-corruption**
(`infrastructure/erp/translation.py`) traduit chaque commande, et elle seule connaît l'ERP :

| Variable | ERP | Domaine | Règle |
|---|---|---|---|
| `weather` | clear, rain, snow, wind | normal, pluie, neige, orage | Terme à terme ; `wind` → `orage`, la condition dégradée la plus proche (**hypothèse**) |
| `delivery_zone` | centre, suburb, rural | centre, proche_banlieue, banlieue, rurale | `suburb` → `banlieue` ; `proche_banlieue` n'est jamais produite par l'ERP |
| `customer_type` | individual, business | standard, premium | `business` → `premium` : les comptes professionnels sont prioritaires (**hypothèse**, à valider avec le métier) |
| `carrier_capacity` | Créneaux restants, de 5 à 50 | Ratio de 0 à 1 | Division par 50 ; une valeur hors de [0, 50] est rejetée |
| `weekend` | Vide avant juillet 2015 | 0 ou 1 | Déduit sans ambiguïté de `day_of_week` |

Règle de qualité : **une valeur qu'on ne sait pas traduire est rejetée, jamais devinée**.
Les lignes rejetées sont comptées par colonne et journalisées (`TranslationReport`), puis
le nettoyage et la validation existants (`data/quality.py`) s'appliquent. L'entraînement
s'arrête si moins de `TRAINING_MIN_ROWS` commandes (200 par défaut) restent exploitables.

### Limite connue : l'ERP ne fournit pas la cible

Ni PostgreSQL ni MongoDB ne contiennent le résultat de la livraison (`express_eligible`).
Sans cible, aucun apprentissage supervisé n'est possible. **En attendant un flux de statuts
de livraison**, la cible est simulée par la règle métier du notebook
(`data/labeling.py`), la même que pour le jeu synthétique. Le modèle apprend donc encore
cette règle, mais sur la distribution réelle des commandes de l'ERP. Le jour où les statuts
réels existeront, seule `MongoErpDatasetSource` changera : elle joindra les statuts au lieu
d'appeler `label_by_business_rule`.

## Conséquences

- Aucune charge ni aucun risque supplémentaire sur la base de production de l'ERP.
- Nouvelle dépendance d'exécution : `pymongo`. Tests : `mongomock` (contrat `OrderStore`
  sans serveur) et un vrai MongoDB en CI (`MONGO_TEST_URI`).
- **Fraîcheur des données = celle de l'ETL.** L'orchestrateur de réentraînement doit tourner
  après l'ETL ; une source vide ou trop pauvre arrête l'entraînement avec une erreur
  explicite au lieu de produire un mauvais modèle.
- **Risque humain** : l'alternant qui maintient MongoDB part bientôt. À faire avant son
  départ : récupérer la documentation de l'ETL et désigner un responsable de la base
  analytique. À défaut, ce point doit remonter à la DSI.
- MongoDB n'impose pas de schéma : c'est l'application qui garantit la qualité (couche
  anti-corruption, puis validation). Toute évolution du format de l'ERP se corrige à un
  seul endroit.
- L'URI MongoDB peut contenir un mot de passe : elle n'apparaît jamais dans les logs
  (`repr=False`) et n'est fournie qu'à l'exécution (jamais dans l'image ni dans Git).
- **Cloud (ADR-0004)** : le service visé pour les commandes devient Azure Cosmos DB for
  MongoDB (vCore) au lieu d'Azure Database for PostgreSQL. Même code, seule l'URI change.
- Les hypothèses de traduction (`wind`, `business`) et la cible simulée sont à valider avec
  le métier ; si elles changent, cette ADR sera remplacée par une nouvelle.
