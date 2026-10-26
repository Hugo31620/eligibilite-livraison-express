# ADR-0006 — Comment sécuriser les entrées et sorties du système

**Status :** Accepté
**Date :** 09/10/2026

## Contexte

L'API reçoit des requêtes venant d'Internet. Elle lit un modèle `joblib` (un *pickle* :
le charger **exécute du code**) et écrit en base. Elle renvoie des décisions et des
messages d'erreur.

Règles du cours :

- On n'expose ni son code ni ses fichiers Python à l'extérieur : **blocage des ports**.
- Il faut un **pare-feu**, un **reverse proxy / API gateway** et une **limitation de
  débit**.

Menaces retenues, d'après l'OWASP API Security Top 10 :

1. Accès direct à l'API ou à la base en contournant le proxy.
2. Saturation : déni de service ou épuisement des crédits cloud par un trop grand nombre de
   requêtes, ou par des requêtes énormes.
3. Données invalides ou malveillantes : champs inattendus, valeurs hors bornes, lots
   géants, identifiants piégés (`../`).
4. Fuite d'information en sortie : traces d'erreur, versions logicielles, carte de l'API
   (`/docs`), réécho des valeurs envoyées.
5. Modèle altéré : un `model.joblib` modifié exécuterait du code à son chargement.
6. Interception en transit.

## Options considérées

| Option | Avantage | Inconvénient |
|---|---|---|
| A. API exposée directement, contrôles dans le code seulement | Simple | L'application devient la seule barrière ; serveur d'application, `/docs` et ports internes visibles ; pas de limitation de débit avant le code Python |
| B. **Défense en profondeur** : pare-feu réseau + reverse proxy nginx (filtrage, débit, taille) + validation stricte dans l'API + sorties maîtrisées | Chaque couche arrête une partie des attaques ; configuration identique en local et dans le cloud ; gratuit (nginx) | Une brique de plus à maintenir |
| C. B + API gateway managée (Azure API Management) ou WAF (Front Door) | Règles OWASP managées, quotas par client, portail développeur | Coût fixe élevé pour un projet d'école (WAF managé) ; redondant avec nginx pour le besoin actuel |

## Décision

**Option B (défense en profondeur)**, avec quatre couches :

### 1. Réseau : un seul port ouvert (blocage des ports)

| Composant | Exposition |
|---|---|
| Proxy nginx | **Seul** point public : 443 (HTTPS) en cloud, `8080` en local |
| API (`uvicorn`, port 8000) | **Réseau interne uniquement** : `expose` sans `ports` en local, *ingress interne* sur Container Apps |
| PostgreSQL, Blob, Key Vault | **Accès privé** (réseau virtuel / *private endpoint*), aucune IP publique |
| SSH, ports d'administration | **Aucun** : Container Apps n'a pas de VM accessible |

- En cloud, **HTTPS seulement** : HTTP est redirigé et le certificat est géré par Azure.
- Le trafic sortant de l'API est limité au strict nécessaire : base, stockage, Key Vault.

### 2. Reverse proxy (`deploy/nginx/nginx.conf`)

- **Liste blanche de chemins** : seuls `/health`, `/health/ready` et `/v1/*` sont transmis.
  Tout le reste (`/docs`, `/openapi.json`, scans de type `/.env`, `/wp-admin`) reçoit un 404
  sans atteindre Python.
- **Méthodes** : `GET` et `POST` uniquement sur `/v1/`.
- **Limitation de débit** : **10 requêtes/s par IP**, rafale de 20, **20 connexions
  simultanées** par IP. Au-delà, réponse 429 au format `Error`.
- **Taille des requêtes** : **1 Mo maximum**, soit environ 3 fois un lot complet de
  1 000 commandes (≈ 350 Ko). Au-delà, réponse 413.
- **Délais** : 10 s pour recevoir une requête, 30 s pour la réponse de l'API (protection
  contre les clients lents).
- **En-têtes** : `server_tokens off` (version nginx masquée), `X-Content-Type-Options`,
  `X-Frame-Options`, `Content-Security-Policy`, `Cache-Control: no-store`.

### 3. Entrées : validation stricte dans l'API

- **Authentification avant toute lecture du corps** : un appelant sans clé valide reçoit
  401 sans apprendre quoi que ce soit du schéma (ADR-0007).
- Schéma Pydantic **fermé** (`extra="forbid"`) et **borné** : `hour` de 0 à 23,
  `carrier_capacity` de 0 à 1, énumérations pour la météo, la zone et le type de client,
  `order_id` limité à `[A-Za-z0-9_-]{1,64}`, lot de 1 à 1 000 commandes.
- Une seule commande invalide **rejette tout le lot**. Pas de traitement partiel silencieux.
- Requêtes SQL **paramétrées** uniquement (pas d'injection). La version du modèle est
  contrôlée au format `X.Y.Z` avant de servir de nom de dossier (pas de `../`).

### 4. Sorties : ne renvoyer que le contrat

- Réponses limitées aux schémas du contrat OpenAPI.
- **Erreurs** : format `Error` (`error`, `message`, `details`). **Aucune trace d'appel**
  (500 = « Erreur interne du serveur » ; le détail part dans les journaux).
- Les valeurs envoyées **ne sont jamais réécrites** dans les messages de validation (testé).
- `/docs` et `/openapi.json` sont **désactivés en production** (`EXPOSE_API_DOCS=false`)
  et bloqués par le proxy. L'en-tête `Server` d'uvicorn est supprimé.
- Les journaux contiennent le **nom** de la clé appelante, jamais sa valeur ni le contenu
  des commandes.

### Intégrité du modèle et de la chaîne logicielle

- L'empreinte **SHA-256 de `model.joblib`** est écrite dans `metadata.json` à
  l'entraînement et **vérifiée avant `joblib.load`**. Un artefact altéré n'est jamais
  désérialisé ; l'API répond 503 (testé).
- L'API n'a qu'un **accès en lecture** aux artefacts : volume `:ro` en local, rôle
  *Storage Blob Data Reader* en cloud.
- L'image est construite en CI, **scannée** (vulnérabilités des dépendances) et tourne en
  **non-root**, avec le système de fichiers en **lecture seule**.

## Conséquences

- Le proxy est sur le chemin de chaque requête. Il fait partie de la stratégie
  blue/green (ADR-0005) au même titre que l'API, et sa configuration est versionnée.
- La limite de 10 requêtes/s par IP peut gêner un client légitime qui passe par une IP
  partagée (NAT d'entreprise). Les gros volumes doivent utiliser
  `/v1/predictions/batch`. La limite est à revoir avec les métriques de la séance 7.
- La limitation par IP ne protège pas d'une attaque distribuée. **Passage à l'option C
  (WAF / API Management)** si l'API devient publique à grande échelle, ou sur
  recommandation de l'expert en cybersécurité.
- **Revue par un expert en cybersécurité avant la mise en production** : relecture de
  cette ADR et de l'ADR-0007, test d'intrusion de l'URL publique, contrôle de la
  configuration réseau Azure. Les points soulevés sont tracés dans de nouvelles ADR.
- Avec la vérification d'empreinte, le point « intégrité des artefacts » laissé ouvert
  par l'ADR-0002 est traité.
