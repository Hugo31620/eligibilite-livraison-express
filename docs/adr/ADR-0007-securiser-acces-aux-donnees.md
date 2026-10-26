# ADR-0007 — Comment sécuriser l'accès à la donnée

**Status :** Accepté
**Date :** 09/10/2026

## Contexte

L'application manipule trois catégories de données :

| Donnée | Sensibilité | Où |
|---|---|---|
| Commandes collectées (`POST /v1/orders`) | Données métier clients | Base des commandes (ADR-0001) |
| Modèle et métriques | Propriété intellectuelle | Artefacts (ADR-0002) |
| Clés d'API | Secret | Fichier d'empreintes / Key Vault |

Règles du cours :

- On donne des **accès limités basés sur des rôles** : `admin`, `user`, `guest`.
- Une **clé d'API** a une date d'expiration (7, 30 ou 90 jours) et doit être **renouvelée
  avant expiration** (rotation).
- On ne met **jamais** les clés dans les fichiers `.env`, ni sur GitHub.
- On peut faire le lien entre une clé d'API et un utilisateur.

Avant cette ADR, toute personne capable d'atteindre l'API pouvait prédire, déposer et
relire n'importe quelle commande.

## Options considérées

| Option | Avantage | Inconvénient |
|---|---|---|
| A. Aucune authentification, filtrage par IP | Rien à développer | Les IP changent et se partagent ; aucun lien avec une personne ; aucun rôle |
| B. **Clé d'API par appelant + rôle**, stockée sous forme d'empreinte, avec expiration | Adaptée à des appels machine à machine ; liée à un nom (audit) ; révocable individuellement ; simple à tester | Les clés doivent être distribuées et renouvelées ; une clé volée reste valable jusqu'à sa révocation ou son expiration |
| C. OAuth 2 / OpenID Connect (Entra ID) avec jetons JWT | Jetons courts, SSO, standard | Nécessite un fournisseur d'identité et une gestion des clients OAuth ; surdimensionné pour l'étape actuelle |
| D. mTLS (certificats clients) | Très robuste | Lourd à distribuer et à renouveler pour chaque appelant |

## Décision

**Option B : une clé d'API nominative par appelant, avec un rôle et une date
d'expiration.**

### Rôles (hiérarchiques : chaque rôle hérite du précédent)

| Route | Public | `guest` | `user` | `admin` |
|---|:-:|:-:|:-:|:-:|
| `GET /health`, `GET /health/ready` (sondes de l'orchestrateur) | ✅ | ✅ | ✅ | ✅ |
| `GET /v1/model` — métadonnées du modèle | ❌ | ✅ | ✅ | ✅ |
| `POST /v1/predictions` et `/v1/predictions/batch` | ❌ | ❌ | ✅ | ✅ |
| `POST /v1/orders` — déposer une commande | ❌ | ❌ | ✅ | ✅ |
| `GET /v1/orders/{id}` — **relire une donnée client** | ❌ | ❌ | ❌ | ✅ |

Principe du **moindre privilège** : un `user` peut écrire une commande mais pas relire
celles des autres. Seul un `admin` accède aux données collectées.

### Clés d'API

- **Envoi** dans l'en-tête `X-API-Key`, jamais dans l'URL : les URL finissent dans les
  journaux et l'historique.
- **Format** `sk_<env>_<256 bits aléatoires>`. L'environnement est lisible : une clé de
  test ne peut pas être confondue avec une clé de production.
- **Stockage** : seule l'**empreinte SHA-256** est conservée, avec le nom, le rôle et la
  date d'expiration. La clé n'est affichée **qu'une fois**, à la création
  (`express-apikey create`). Une fuite du fichier ne révèle donc aucune clé.
- **Expiration** : 90 jours **maximum** (refusé au-delà) ; 7 ou 30 jours pour les accès
  ponctuels.
- **Rotation** : une nouvelle clé est créée **avant** l'expiration de l'ancienne. Les deux
  coexistent le temps que l'appelant bascule, puis l'ancienne est révoquée
  (`express-apikey revoke`). Le fichier est **relu à chaud** : ni la rotation ni la
  révocation ne demandent de redémarrer l'API (testé).
- **Où vit le fichier d'empreintes** :
  - en local, dans `secrets/api_keys.json`, ignoré par Git et monté **en lecture seule**
    dans le conteneur ;
  - en cloud, dans un **secret Azure Key Vault**, monté dans Container Apps par référence
    au Key Vault.

  Ce fichier n'est **jamais** dans `.env`, ni dans l'image, ni dans le dépôt.
- **Réponses** :
  - 401 avec un **message identique** pour une clé absente, inconnue ou expirée (on ne
    renseigne pas un attaquant) ;
  - 403 si le rôle est insuffisant.

  L'authentification a lieu **avant** la validation du corps de la requête.
- **Audit** : chaque refus est journalisé avec le **nom** de la clé (jamais sa valeur).

### Accès des services aux données (cloud)

- **Aucun mot de passe de service** : l'API et le job d'entraînement s'authentifient
  auprès de PostgreSQL, Blob Storage et Key Vault par **identité managée**.
- **Moindre privilège par composant** :

  | Composant | Base des commandes | Artefacts (Blob) | Key Vault |
  |---|---|---|---|
  | API | `INSERT` + `SELECT` sur `orders` uniquement | **Lecture** | Lecture du secret des clés |
  | Job d'entraînement | `SELECT` (pour les futurs entraînements sur données réelles) | Écriture | — |
  | Humains (admin) | Aucun accès direct permanent : accès **temporaire et journalisé** si besoin | Lecture | Gestion des secrets |

- **Chiffrement** :
  - au repos, activé par défaut sur PostgreSQL, Blob et Key Vault ;
  - en transit, TLS obligatoire, y compris vers la base.
- **Sauvegardes** : sauvegardes automatiques PostgreSQL et *soft delete* + versioning sur
  Blob (protection contre la suppression accidentelle ou malveillante).
- **Minimisation** : le schéma des commandes ne contient **aucune donnée identifiante**
  (ADR-0001). Toute évolution qui en ajouterait doit repasser par une ADR.

### Données d'entraînement et de test

- Hors production, on n'utilise que des **données synthétiques ou anonymisées**.
- Les clés de test des tests automatisés sont factices (`sk_test_*`) et n'existent dans
  aucun environnement.

## Conséquences

- Implémentation :
  - domaine `domain/security.py` (rôles, empreintes) ;
  - port `ApiKeyStore` et adaptateur `JsonFileApiKeyStore` ;
  - service `AuthenticationService` et dépendance FastAPI `require(Role.X)` ;
  - commande `express-apikey create|list|revoke` ;
  - tests de la matrice complète rôle × route, plus clé absente, inconnue et expirée.
- **Écart au contrat `openapi.yml`** : le contrat ne déclare ni `securitySchemes` ni les
  réponses 401/403. Elles sont ajoutées à l'API générée. **Le contrat doit être mis à jour
  avec l'intervenant**. Le test de contrat vérifie que toute route `/v1` déclare l'en-tête.
- Tant qu'aucune clé n'est créée, toutes les routes `/v1` répondent 401 (« fermé par
  défaut »). Il faut créer une clé avant le premier appel (voir le README).
- Une clé volée reste valable jusqu'à sa révocation, au plus 90 jours. **Passage à
  l'option C (OAuth 2 / Entra ID, jetons d'une heure)** dès qu'il y aura des utilisateurs
  humains ou plus d'une dizaine d'applications clientes.
- **Les rôles et cette matrice sont soumis à l'expert en cybersécurité** avec
  l'ADR-0006, avant la mise en production.
