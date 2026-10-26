"""Gestion des clés d'API : ``express-apikey create|list|revoke`` (ADR-0007).

La clé n'est affichée qu'**une seule fois**, à la création ; seule son empreinte est stockée.
"""

import argparse
import sys
from collections.abc import Sequence
from datetime import timedelta

from eligibilite_livraison.config import Settings
from eligibilite_livraison.domain.errors import DomainError
from eligibilite_livraison.domain.security import (
    MAX_KEY_LIFETIME_DAYS,
    ApiKeyRecord,
    Role,
    generate_api_key,
    hash_api_key,
    utc_now,
)
from eligibilite_livraison.infrastructure.factory import build_infrastructure


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="express-apikey", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Crée une clé et l'affiche une seule fois.")
    create.add_argument("--name", required=True, help="Titulaire (ex. alice, batch-nuit).")
    create.add_argument("--role", required=True, choices=[role.value for role in Role])
    create.add_argument(
        "--days",
        type=int,
        default=MAX_KEY_LIFETIME_DAYS,
        help=f"Durée de validité, {MAX_KEY_LIFETIME_DAYS} jours maximum (défaut).",
    )

    commands.add_parser("list", help="Liste les clés (noms, rôles, expirations).")

    revoke = commands.add_parser("revoke", help="Révoque immédiatement une clé.")
    revoke.add_argument("--name", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        settings = Settings.from_env()
        store = build_infrastructure(settings).api_key_store
        if args.command == "create":
            if not 1 <= args.days <= MAX_KEY_LIFETIME_DAYS:
                print(f"--days doit être entre 1 et {MAX_KEY_LIFETIME_DAYS}.", file=sys.stderr)
                return 2
            raw_key = generate_api_key(settings.env)
            expires_at = utc_now() + timedelta(days=args.days)
            store.add(ApiKeyRecord(args.name, Role(args.role), hash_api_key(raw_key), expires_at))
            print(
                f"Clé {args.role!r} créée pour {args.name!r}, "
                f"valable jusqu'au {expires_at:%d/%m/%Y}."
            )
            print("Copiez-la maintenant, elle ne sera plus jamais affichée :")
            print(raw_key)
        elif args.command == "list":
            now = utc_now()
            for record in sorted(store.list_all(), key=lambda item: item.expires_at):
                remaining = f"{(record.expires_at - now).days} j"
                status = "EXPIRÉE" if record.is_expired(now) else remaining
                expiry = f"{record.expires_at:%d/%m/%Y}"
                print(f"{record.name:<20} {record.role.value:<6} {expiry}  {status}")
        elif not store.revoke(args.name):
            print(f"Aucune clé nommée {args.name!r}.", file=sys.stderr)
            return 1
        else:
            print(f"Clé {args.name!r} révoquée.")
    except DomainError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
