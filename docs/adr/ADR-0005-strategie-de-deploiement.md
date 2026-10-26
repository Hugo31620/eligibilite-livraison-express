# ADR-0005 — Quelle stratégie de déploiement

**Status :** Accepté
**Date :** 09/10/2026

## Contexte

Une nouvelle version peut changer **le code**, **le modèle** (`MODEL_VERSION`), ou les deux.
Un modèle peut être techniquement valide (l'API répond 200) et pourtant **moins bon
métier** : par exemple, il refuse l'express à des commandes qui y avaient droit. Cette
dérive ne se voit pas dans les codes HTTP.

Contraintes retenues :

- **Aucune interruption de service** : les commandes arrivent toute la journée.
- **Retour arrière en moins d'une minute**, sans reconstruire ni redéployer.
- **Volume de trafic modeste** : quelques milliers de prédictions par jour au départ.
- Une seule équipe, une seule API : pas de dépendances croisées entre services à orchestrer.
- La plateforme (Azure Container Apps, ADR-0004) sait faire tourner **plusieurs
  révisions**, leur donner un **label** avec une URL dédiée et **répartir le trafic** par
  pourcentage.

## Options considérées

| Option | Avantage | Inconvénient |
|---|---|---|
| Big Bang Release | Simple, planifiable (ex. 2 h du matin) | Coupure pendant le déploiement ; retour arrière = redéploiement complet ; tout le monde subit un éventuel défaut |
| Déploiement par service | Limite l'étendue de chaque déploiement | Sans objet : une seule API |
| Rolling | Pas besoin de doubler les ressources | Deux versions servent en même temps de façon **non contrôlée** pendant la transition ; retour arrière lent (il faut « re-rouler ») |
| Canary (10 % → 50 % → 100 %) | Limite le nombre d'utilisateurs exposés ; mesure sur du vrai trafic | Avec peu de trafic, 10 % des requêtes ne suffit pas pour une comparaison **statistiquement fiable** ; plusieurs jours par version |
| Déploiement pilote | Proche du canary, ciblé sur une population | Il faudrait un critère de séparation des clients, inexistant dans le contrat actuel |
| Shadow (miroir) | Idéal pour comparer **deux modèles** sur les mêmes requêtes, sans risque | Double le coût de calcul ; la duplication des requêtes n'est pas native dans Container Apps ; les écritures (commandes) ne doivent pas être doublées |
| **Blue / Green** | Bascule et retour arrière **instantanés** (déplacement de trafic) ; la nouvelle version est testée en conditions réelles **avant** de recevoir du trafic ; supporté nativement par la plateforme | Deux versions tournent en même temps pendant la bascule (coût doublé quelques heures) ; tout le trafic bascule d'un coup |

## Décision

**Blue / Green, avec les révisions d'Azure Container Apps** (mode « multiple revisions »).
Le **rollback** et le **hotfix** sont deux usages de ce même mécanisme.

Déroulé d'une mise en production :

1. La CI construit l'image, lance `pytest`, scanne l'image puis la pousse dans le registre
   avec le **hash du commit** comme tag.
2. Déploiement d'une nouvelle révision portant le label libre (par exemple `green`), avec
   **0 % du trafic**. `blue` continue de servir 100 % du trafic.
3. **Tests de fumée sur l'URL du label** `green` : `/health/ready` = 200, `/v1/model`
   renvoie la version attendue, une prédiction de référence donne la décision attendue
   (commandes `VALID_ORDER` / `HARD_ORDER` des tests).
4. **Bascule** : `green = 100 %`, `blue = 0 %`. La révision `blue` reste active **24 h**.
5. **Retour arrière** pendant ces 24 h : `blue = 100 %`. C'est une seule commande, sans
   reconstruction.
6. Après 24 h sans incident, `blue` est désactivée. Au déploiement suivant, les rôles
   s'inversent.

- **Hotfix** : même chaîne, en accéléré (revue réduite à une personne). Les tests et le
  scan **ne sont jamais sautés**.
- **Changement de modèle seul** : on déploie la même image avec une autre `MODEL_VERSION`.
  Cela crée une nouvelle révision, donc la même procédure s'applique.

**Évolutions prévues :**

- **Shadow pour les nouveaux modèles**, dès qu'il y aura du trafic réel. Le nouveau modèle
  calcule ses prédictions sur une copie des requêtes, sans les renvoyer. On compare les
  taux de « oui » et les probabilités avant toute bascule.
- **Canary**, dès que le volume rendra une comparaison sur 10 % significative. La
  plateforme le permet déjà (pondération `90/10`).

## Conséquences

- Les deux révisions partagent la **même base de commandes**. Un changement de schéma doit
  donc être **rétrocompatible** pendant 24 h : on ajoute une colonne, et on ne la supprime
  qu'au déploiement suivant.
- Coût : deux révisions actives pendant quelques heures par déploiement. C'est négligeable
  avec la facturation à l'usage de Container Apps.
- Chaque prédiction renvoie `model_version` : on sait toujours quelle version a répondu,
  y compris pendant la bascule.
- Les commandes de bascule et de retour arrière sont **scriptées dans la CI** (séance 3).
  Personne ne les tape à la main en production.
- Un tableau de bord comparant les taux de « oui » par `model_version` (séance 7)
  conditionnera le passage au canary et au shadow.
