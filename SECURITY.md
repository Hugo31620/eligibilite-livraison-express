# Politique de sécurité

## Versions maintenues

| Version | Correctifs de sécurité |
|---|---|
| 1.0.x | ✅ |
| < 1.0 | ❌ (versions de développement, jamais publiées) |

Seule la dernière version mineure reçoit des correctifs. Quand une version `X.Y+1.0` sort,
`X.Y.z` reste maintenue **3 mois** pour laisser le temps de migrer.

## Signaler une vulnérabilité

**N'ouvrez pas d'issue publique.** Utilisez le signalement privé de GitHub :
onglet **Security** → **Report a vulnerability**
(ou contactez le mainteneur, [@Hugo31620](https://github.com/Hugo31620)).

Indiquez :

- la version touchée (tag ou `GET /v1/model`) ;
- le composant (API, authentification, image Docker, proxy nginx, dépendance…) ;
- les étapes de reproduction et l'impact estimé ;
- si possible, une proposition de correctif.

Ne joignez jamais de vraie clé d'API ni de donnée client.

## Délais de traitement

| Étape | Délai maximal |
|---|---|
| Accusé de réception | 3 jours ouvrés |
| Évaluation et score de gravité (CVSS) | 7 jours ouvrés |
| Correctif — gravité critique | 7 jours |
| Correctif — élevée | 30 jours |
| Correctif — moyenne ou faible | prochaine version mineure |

Le correctif est publié dans une branche `hotfix/X.Y.Z`, puis annoncé dans le
[CHANGELOG](CHANGELOG.md) (section `Security`) et dans un *GitHub Security Advisory*.
Un identifiant **CVE** est demandé via GitHub pour toute vulnérabilité de gravité moyenne ou
plus. La personne qui a signalé la faille est créditée si elle le souhaite.

## Périmètre

Dans le périmètre : le code de ce dépôt, l'image Docker publiée sur `ghcr.io`, la
configuration `docker-compose.yml` et `deploy/`.

Hors périmètre : les dépendances tierces (à signaler à leur projet ; nous mettons à jour la
version dès qu'un correctif existe), les attaques par déni de service volumétrique, les
déploiements modifiés par un tiers.

## Mesures en place

Résumé ; le détail est dans [ADR-0006](docs/adr/ADR-0006-securiser-entrees-sorties.md) et
[ADR-0007](docs/adr/ADR-0007-securiser-acces-aux-donnees.md).

- Clés d'API nominatives, stockées hachées (SHA-256), expirant en 90 jours au plus ;
  accès par rôle (`guest`, `user`, `admin`).
- Conteneur non-root, système de fichiers en lecture seule, capacités Linux retirées,
  aucun secret ni `.env` dans l'image.
- Seul le reverse proxy est exposé ; limitation de débit et taille des requêtes bornée.
- Empreinte SHA-256 du modèle vérifiée avant chargement.
- Dépendances et image analysées à chaque PR par la CI.
