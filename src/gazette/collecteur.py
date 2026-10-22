"""Un passage de collecte sur toutes les sources actives.

Les sources sont lues une par une : pas de parallélisme sur un même éditeur.
Chaque source donne une ligne de journal et une ligne dans la table passages.
"""

import argparse
import logging
import os
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
import psycopg

from gazette import migrations
from gazette.collecte import (
    ATTENTES_S,
    ErreurCollecte,
    Telechargement,
    items_bruts,
    nouveau_client,
    robots_autorise,
    telecharger,
)
from gazette.depot import DepotPostgres, EtatSource, Passage, dsn_depuis_environnement
from gazette.journal import configurer, tracer
from gazette.sources import charger_sources
from gazette.stockage import ArticlesBruts

SEUIL_SOMMEIL = 3


def collecter_source(
    etat: EtatSource,
    client: httpx.Client,
    stockage: ArticlesBruts,
    robots: dict[str, bool],
    attentes: Sequence[float],
    pause: Callable[[float], None],
) -> tuple[Passage, Telechargement | None]:
    debut = datetime.now(UTC)
    chrono = time.monotonic()
    passage = Passage(source=etat.nom, debut=debut, duree_ms=0, statut="echec")
    telechargement = None
    try:
        hote = urlparse(etat.url_flux).netloc
        if hote not in robots:
            robots[hote] = robots_autorise(client, etat.url_flux)
        if not robots[hote]:
            raise ErreurCollecte("robots.txt interdit ce flux")
        telechargement = telecharger(
            client, etat.url_flux, etat.etag, etat.last_modified, attentes, pause
        )
        passage.code_http = telechargement.code_http
        if telechargement.contenu is None:
            passage.statut = "non_modifie"
        else:
            items, sans_lien = items_bruts(telechargement.contenu, etat.nom, debut)
            ecrits = sum(stockage.ecrire(item) for item in items)
            passage.statut = "ok"
            passage.recus = len(items) + sans_lien
            passage.ecrits = ecrits
            passage.ignores = passage.recus - ecrits
    except ErreurCollecte as erreur:
        passage.code_http = passage.code_http or erreur.code_http
        passage.erreur = str(erreur)
        telechargement = None
    except Exception as erreur:
        passage.erreur = f"{type(erreur).__name__} : {erreur}"
        telechargement = None
    passage.duree_ms = round((time.monotonic() - chrono) * 1000)
    return passage, telechargement


def collecter_tout(
    depot,
    stockage: ArticlesBruts,
    client: httpx.Client,
    attentes: Sequence[float] = ATTENTES_S,
    pause: Callable[[float], None] = time.sleep,
) -> dict:
    bilan = {"sources": 0, "ok": 0, "echecs": 0, "recus": 0, "ecrits": 0, "ignores": 0}
    endormies = []
    robots: dict[str, bool] = {}
    for etat in depot.lister(actives_seulement=True):
        passage, telechargement = collecter_source(etat, client, stockage, robots, attentes, pause)
        depot.noter_passage(passage)
        if passage.statut == "echec":
            if depot.noter_echec(etat.nom, passage.erreur, SEUIL_SOMMEIL):
                endormies.append(etat.nom)
                tracer(
                    "source_en_sommeil",
                    logging.ERROR,
                    source=etat.nom,
                    echecs=etat.echecs_consecutifs + 1,
                    erreur=passage.erreur,
                )
        else:
            depot.noter_reussite(etat.nom, telechargement.etag, telechargement.last_modified)
        tracer(
            "source_collectee",
            logging.INFO if passage.statut != "echec" else logging.WARNING,
            source=passage.source,
            statut=passage.statut,
            code_http=passage.code_http,
            recus=passage.recus,
            ecrits=passage.ecrits,
            ignores=passage.ignores,
            duree_ms=passage.duree_ms,
            erreur=passage.erreur,
        )
        bilan["sources"] += 1
        bilan["ok" if passage.statut != "echec" else "echecs"] += 1
        for compteur in ("recus", "ecrits", "ignores"):
            bilan[compteur] += getattr(passage, compteur)
    bilan["endormies"] = endormies
    bilan["en_sommeil"] = [e.nom for e in depot.lister() if not e.actif]
    tracer("collecte_terminee", **bilan)
    return bilan


def executer(dsn: str, chemin_sources: Path, racine: Path) -> dict:
    """Migrations, synchronisation de sources.csv, puis un passage de collecte."""
    with psycopg.connect(dsn, autocommit=True) as connexion:
        migrations.appliquer(connexion)
        depot = DepotPostgres(connexion)
        depot.synchroniser(charger_sources(chemin_sources))
        with nouveau_client() as client:
            return collecter_tout(depot, ArticlesBruts(racine), client)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Un passage de collecte sur les sources actives")
    parser.add_argument(
        "--sources", type=Path, default=Path(os.environ.get("GAZETTE_SOURCES", "sources.csv"))
    )
    parser.add_argument(
        "--sortie",
        type=Path,
        default=Path(os.environ.get("GAZETTE_ARTICLES_BRUTS", "data/articles_bruts")),
    )
    args = parser.parse_args(argv)
    configurer()
    executer(dsn_depuis_environnement(), args.sources, args.sortie)
    return 0


if __name__ == "__main__":
    sys.exit(main())
