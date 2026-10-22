"""État des sources : dernière réussite, échecs, sommeil, et articles bruts par source."""

import argparse
import os
import sys
from pathlib import Path

import psycopg

from gazette.depot import DepotPostgres, dsn_depuis_environnement
from gazette.stockage import ArticlesBruts, slug


def _date(valeur) -> str:
    return f"{valeur:%Y-%m-%d %H:%M}" if valeur else "-"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="État des sources de collecte")
    parser.add_argument("--reactiver", metavar="NOM", help="sortir une source du sommeil")
    parser.add_argument(
        "--articles",
        type=Path,
        default=Path(os.environ.get("GAZETTE_ARTICLES_BRUTS", "data/articles_bruts")),
    )
    args = parser.parse_args(argv)

    with psycopg.connect(dsn_depuis_environnement(), autocommit=True) as connexion:
        depot = DepotPostgres(connexion)
        if args.reactiver:
            if not depot.reactiver(args.reactiver):
                print(f"Source inconnue : {args.reactiver}", file=sys.stderr)
                return 1
            print(f"{args.reactiver} réactivée")
            return 0
        etats = depot.lister()

    articles = ArticlesBruts(args.articles).compter()
    print(f"{'source':<18}{'actif':<7}{'echecs':<8}{'derniere reussite':<19}{'articles':<10}erreur")
    for e in etats:
        print(
            f"{e.nom:<18}{'oui' if e.actif else 'NON':<7}{e.echecs_consecutifs:<8}"
            f"{_date(e.derniere_reussite):<19}{articles.get(slug(e.nom), 0):<10}"
            f"{e.derniere_erreur or ''}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
