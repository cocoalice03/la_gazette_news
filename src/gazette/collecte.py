"""Lecture d'un flux RSS ou Atom et écriture de ses items en JSON.

Seuls le titre, un extrait tronqué, le lien, la date et la rubrique sont conservés.
L'auteur n'est pas stocké : c'est une donnée personnelle.
"""

import argparse
import calendar
import html
import json
import re
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import feedparser
import httpx

from gazette import USER_AGENT
from gazette.sources import charger_sources, trouver_source

LONGUEUR_MAX_EXTRAIT = 300
DELAI_REQUETE_S = 20.0

_BALISES = re.compile(r"<[^>]+>")
_ESPACES = re.compile(r"\s+")


def nettoyer_extrait(texte: str | None) -> str:
    if not texte:
        return ""
    texte = _ESPACES.sub(" ", html.unescape(_BALISES.sub(" ", texte))).strip()
    if len(texte) <= LONGUEUR_MAX_EXTRAIT:
        return texte
    coupe = texte[:LONGUEUR_MAX_EXTRAIT].rsplit(" ", 1)[0]
    return coupe.rstrip(" ,;:.") + "…"


def _date_iso(entree: dict) -> str | None:
    date = entree.get("published_parsed") or entree.get("updated_parsed")
    if date is None:
        return None
    return datetime.fromtimestamp(calendar.timegm(date), tz=UTC).isoformat()


def _rubrique(entree: dict, lien: str) -> str | None:
    etiquettes = entree.get("tags") or []
    if etiquettes and etiquettes[0].get("term"):
        return etiquettes[0]["term"].strip()
    segments = [s for s in urlparse(lien).path.split("/") if s]
    return segments[0] if len(segments) > 1 else None


def parser_flux(contenu: bytes, source: str) -> tuple[list[dict], int]:
    """Retourne les items valides et le nombre d'items écartés.

    Un item est écarté s'il lui manque un titre, un lien ou une date.
    """
    flux = feedparser.parse(contenu)
    items, ecartes = [], 0
    for entree in flux.entries:
        titre = _ESPACES.sub(" ", html.unescape(entree.get("title", ""))).strip()
        lien = entree.get("link", "").strip()
        date = _date_iso(entree)
        if not (titre and lien and date):
            ecartes += 1
            continue
        items.append(
            {
                "source": source,
                "titre": titre,
                "lien": lien,
                "date_publication": date,
                "extrait": nettoyer_extrait(entree.get("summary")),
                "rubrique": _rubrique(entree, lien),
                "guid": entree.get("id") or lien,
            }
        )
    return items, ecartes


def robots_autorise(url: str, client: httpx.Client) -> bool:
    morceaux = urlparse(url)
    reponse = client.get(f"{morceaux.scheme}://{morceaux.netloc}/robots.txt")
    if reponse.status_code >= 400:
        return True
    analyseur = RobotFileParser()
    analyseur.parse(reponse.text.splitlines())
    return analyseur.can_fetch(USER_AGENT, url)


def telecharger(url: str, client: httpx.Client) -> bytes:
    reponse = client.get(url)
    reponse.raise_for_status()
    return reponse.content


def _slug(texte: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")


def collecter(nom_source: str, chemin_sources: Path, dossier_sortie: Path) -> Path:
    source = trouver_source(charger_sources(chemin_sources), nom_source)
    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=DELAI_REQUETE_S,
        follow_redirects=True,
    ) as client:
        if not robots_autorise(source.acces, client):
            raise PermissionError(f"robots.txt interdit {source.acces}")
        contenu = telecharger(source.acces, client)

    recupere_le = datetime.now(UTC)
    items, ecartes = parser_flux(contenu, source.nom)
    for item in items:
        item["recupere_le"] = recupere_le.isoformat()

    dossier_sortie.mkdir(parents=True, exist_ok=True)
    fichier = dossier_sortie / f"{_slug(source.nom)}-{recupere_le:%Y%m%dT%H%M%SZ}.json"
    fichier.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "evenement": "collecte_terminee",
                "source": source.nom,
                "items": len(items),
                "ecartes": ecartes,
                "fichier": str(fichier),
            },
            ensure_ascii=False,
        )
    )
    return fichier


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collecte d'une source de sources.csv")
    parser.add_argument("--source", required=True, help="valeur de la colonne nom")
    parser.add_argument("--sources", type=Path, default=Path("sources.csv"))
    parser.add_argument("--sortie", type=Path, default=Path("data/brut"))
    args = parser.parse_args(argv)
    try:
        collecter(args.source, args.sources, args.sortie)
    except (KeyError, PermissionError, httpx.HTTPError) as erreur:
        print(
            json.dumps({"evenement": "collecte_echec", "erreur": str(erreur)}, ensure_ascii=False)
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
