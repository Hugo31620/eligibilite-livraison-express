# ADR-0004 — Cloud, on-premise ou local ? Et quels services cloud ?

**Status :** Accepté
**Date :** 09/10/2026

## Contexte

L'image Docker (ADR-0003) doit tourner quelque part, en **test** puis en **production**.

Contraintes retenues :

- L'API doit être **joignable par d'autres systèmes**, 24 h/24, avec des pics de charge.
- **Budget d'école** : quelques dizaines d'euros par mois au maximum. Personne n'est
  d'astreinte sur du matériel.
- **Données de commandes clients** : le schéma ne contient aucune donnée identifiante
  (ADR-0001). Elles restent toutefois des données métier, à héberger **dans l'Union
  européenne** (RGPD).
- Le déploiement doit permettre de **faire cohabiter deux versions** et de **basculer le
  trafic** (ADR-0005).
- Il faut pouvoir **chiffrer, isoler le réseau et gérer des secrets** sans tout construire
  soi-même (ADR-0006, ADR-0007).
- L'ADR-0001 et l'ADR-0002 annoncent le passage de SQLite à PostgreSQL, et d'un dossier
  local à un stockage partagé, dès qu'il y aura plusieurs instances.

## Options considérées

| Option | Avantage | Inconvénient |
|---|---|---|
| A. Local (poste du développeur) | Gratuit, immédiat | Pas joignable de l'extérieur, s'arrête avec le PC, aucune sauvegarde : acceptable **uniquement pour le développement** |
| B. On-premise (serveur dans les locaux) | Maîtrise totale des données et du réseau | Matériel à acheter, électricité, maintenance, sauvegardes et sécurité physique à notre charge ; capacité fixe (pas d'élasticité) ; délai de mise en place |
| C. **Cloud public (Azure)** | Élasticité, services managés (base, secrets, journaux), régions UE, paiement à l'usage, crédits étudiants | Dépendance à un fournisseur, coûts à surveiller, compétences cloud à acquérir |
| D. Cloud public (AWS / GCP) | Mêmes atouts techniques que C | Équivalents fonctionnels, sans avantage décisif pour ce projet |

**Entre Azure, AWS et GCP**, les trois conviennent techniquement. Azure l'emporte ici pour
trois raisons pratiques : **crédits Azure for Students**, **régions françaises** (France
Central, Paris), et un service de conteneurs serverless qui gère **nativement le
blue/green** (Container Apps : révisions, labels, répartition du trafic).

## Décision

- **Développement : local** (option A), avec `docker compose` qui reproduit la topologie
  cible.
- **Test et production : cloud Azure** (option C), région **France Central**.
  Chaque environnement a son propre *resource group* et ses propres secrets ; aucune
  ressource n'est partagée entre test et prod.

### Services retenus

| Besoin | Service Azure | Pourquoi |
|---|---|---|
| Exécuter les conteneurs | **Azure Container Apps** (plan Consumption) | Serverless : pas de VM à patcher, mise à l'échelle automatique (y compris à 0 hors heures), révisions et répartition du trafic pour le blue/green (ADR-0005), ingress HTTPS géré |
| Porte d'entrée publique | **Container App `proxy`** (nginx, ingress *externe*, HTTPS seulement) | Même configuration qu'en local : filtrage des chemins et limitation de débit (ADR-0006) |
| API | **Container App `api`** (ingress *interne* uniquement) | **Inaccessible depuis Internet** : seul le proxy peut l'appeler (blocage des ports) |
| Entraînement | **Container Apps Job** (déclenché manuellement ou planifié) | Même image, ne tourne que le temps de l'entraînement |
| Images | **Azure Container Registry** (Basic) | Registre privé, scan de vulnérabilités, accès par identité managée |
| Commandes | **Azure Database for PostgreSQL – Flexible Server** (Burstable B1ms), accès réseau **privé** | Remplace SQLite dès qu'il y a plusieurs instances (ADR-0001) ; sauvegardes automatiques |
| Artefacts du modèle | **Azure Blob Storage** (conteneur privé, versioning activé) | Partagé entre le job d'entraînement et l'API ; remplace le dossier local (ADR-0002) |
| Secrets et clés d'API | **Azure Key Vault** | Empreintes des clés d'API, chaîne de connexion : jamais dans un `.env` ni dans Git (ADR-0007) |
| Identité des services | **Identités managées** + Azure RBAC | Aucun mot de passe de service dans le code ou la configuration |
| Journaux | **Log Analytics** (intégré à Container Apps) | Traçabilité des accès (nom de la clé, jamais sa valeur) ; base de la supervision de la séance 7 |

### Coût visé

- **Container Apps** : le plan Consumption inclut chaque mois **180 000 vCPU-secondes,
  360 000 GiB-secondes et 2 millions de requêtes** gratuits par abonnement. Le trafic d'un
  projet d'école tient dans cette franchise.
- **Coûts fixes principaux** : PostgreSQL Burstable et le registre Basic, soit quelques
  dizaines d'euros par mois **au total**, couverts par les crédits étudiants.
- Ces montants sont à **reconfirmer avec la calculatrice de prix Azure** avant la
  création des ressources. Un **budget avec alerte** est créé sur l'abonnement dès le
  premier jour.

## Conséquences

- Il faut écrire les adaptateurs `infrastructure/azure/` (`PostgresOrderStore`,
  `BlobModelRepository`) et les déclarer dans `infrastructure/factory.py` pour
  `APP_ENV=test|prod`. L'API et les services ne changent pas (ports ADR-0001 et ADR-0002).
  Le test de contrat `tests/integration/test_order_store.py` devra passer sur PostgreSQL.
- L'infrastructure est décrite **en code** (Bicep ou Terraform), versionnée avec
  l'application et relue en revue. Aucune ressource n'est créée « à la main » dans le
  portail.
- L'application dépend d'Azure **uniquement via ses adaptateurs**. Passer à AWS ou GCP
  demanderait de réécrire `infrastructure/<cloud>/` et l'infrastructure en code, pas le
  métier.
- **Dès que de vraies données personnelles entreront dans le schéma**, cette ADR devra
  être relue avec le DPO (localisation, durée de conservation) et un expert en
  cybersécurité.
