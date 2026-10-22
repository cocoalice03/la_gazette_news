"""Téléchargement poli d'un flux RSS ou Atom et conversion de ses entrées en items bruts.

On garde le titre, un extrait tronqué, le lien, la date, la rubrique et les métadonnées de
l'entrée. Le texte intégral, les images, les commentaires et l'auteur (donnée personnelle)
sont retirés, y compris du payload.
"""

import calendar
import gzip
import hashlib
import html
import json
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import feedparser
import httpx

from gazette import USER_AGENT

LONGUEUR_MAX_EXTRAIT = 300
DELAI_REQUETE_S = 20.0
ATTENTES_S = (2.0, 8.0)
CODES_TRANSITOIRES = frozenset({408, 425, 429, 500, 502, 503, 504})
CHAMPS_EXCLUS = frozenset(
    {
        "author",
        "author_detail",
        "authors",
        "contributors",
        "publisher",
        "publisher_detail",
        "content",
        "media_content",
        "media_thumbnail",
        "media_credit",
        "credit",
        "enclosures",
        "image",
        "comments",
        "wfw_commentrss",
        "slash_comments",
    }
)

_BALISES = re.compile(r"<[^>]+>")
_ESPACES = re.compile(r"\s+")


class ErreurCollecte(Exception):
    def __init__(self, motif: str, code_http: int | None = None):
        super().__init__(motif)
        self.code_http = code_http


@dataclass(frozen=True)
class Telechargement:
    code_http: int
    contenu: bytes | None
    etag: str | None
    last_modified: str | None


def nouveau_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=DELAI_REQUETE_S,
        follow_redirects=True,
        transport=transport,
    )


def robots_autorise(client: httpx.Client, url: str) -> bool:
    morceaux = urlparse(url)
    try:
        reponse = client.get(f"{morceaux.scheme}://{morceaux.netloc}/robots.txt")
    except httpx.HTTPError:
        return True
    if reponse.status_code >= 400:
        return True
    analyseur = RobotFileParser()
    analyseur.parse(reponse.text.splitlines())
    return analyseur.can_fetch(USER_AGENT, url)


def telecharger(
    client: httpx.Client,
    url: str,
    etag: str | None = None,
    last_modified: str | None = None,
    attentes: Sequence[float] = ATTENTES_S,
    pause: Callable[[float], None] = time.sleep,
) -> Telechargement:
    """GET conditionnel. Réessaie les erreurs transitoires après chaque attente de `attentes`.

    Lève ErreurCollecte sur une erreur permanente (404, 403...) ou quand les essais sont épuisés.
    """
    entetes = {}
    if etag:
        entetes["If-None-Match"] = etag
    if last_modified:
        entetes["If-Modified-Since"] = last_modified

    echec = ErreurCollecte("aucune tentative")
    for tentative in range(len(attentes) + 1):
        if tentative:
            pause(attentes[tentative - 1])
        try:
            reponse = client.get(url, headers=entetes)
        except httpx.TransportError as erreur:
            echec = ErreurCollecte(f"{type(erreur).__name__} : {erreur}")
            continue
        code = reponse.status_code
        if code == 304:
            return Telechargement(304, None, etag, last_modified)
        if code < 400:
            return Telechargement(
                code,
                _decompresser(reponse.content),
                reponse.headers.get("ETag"),
                reponse.headers.get("Last-Modified"),
            )
        echec = ErreurCollecte(f"HTTP {code}", code)
        if code not in CODES_TRANSITOIRES:
            raise echec
    raise echec


def _decompresser(contenu: bytes) -> bytes:
    """Certains éditeurs servent du gzip sans l'en-tête Content-Encoding."""
    return gzip.decompress(contenu) if contenu[:2] == b"\x1f\x8b" else contenu


def nettoyer_extrait(texte: str | None) -> str:
    if not texte:
        return ""
    texte = _ESPACES.sub(" ", html.unescape(_BALISES.sub(" ", texte))).strip()
    if len(texte) <= LONGUEUR_MAX_EXTRAIT:
        return texte
    coupe = texte[:LONGUEUR_MAX_EXTRAIT].rsplit(" ", 1)[0]
    return coupe.rstrip(" ,;:.") + "…"


def identifiant(source: str, lien: str) -> str:
    return hashlib.sha256(f"{source}\n{lien}".encode()).hexdigest()[:32]


def _texte(valeur: str | None) -> str | None:
    texte = _ESPACES.sub(" ", html.unescape(valeur or "")).strip()
    return texte or None


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


def _payload(entree: dict) -> dict:
    payload = {}
    for cle, valeur in entree.items():
        if cle in CHAMPS_EXCLUS or cle.endswith("_parsed"):
            continue
        if cle == "links":
            valeur = [lien for lien in valeur if lien.get("rel") != "enclosure"]
        payload[cle] = valeur
    return json.loads(json.dumps(payload, default=str))


def items_bruts(contenu: bytes, source: str, recupere_le: datetime) -> tuple[list[dict], int]:
    """Retourne les items du flux et le nombre d'entrées ignorées faute de lien.

    Un flux sans aucune entrée est une erreur : un flux de presse vide est un flux cassé.
    Un item sans titre ou sans date est gardé tel quel : le tri revient au nettoyage.
    """
    flux = feedparser.parse(contenu)
    if not flux.entries:
        if flux.get("bozo") or not flux.get("version"):
            motif = flux.get("bozo_exception") or "ni RSS ni Atom"
            raise ErreurCollecte(f"flux illisible : {motif}")
        raise ErreurCollecte("flux vide")
    items, sans_lien = [], 0
    for entree in flux.entries:
        lien = (entree.get("link") or "").strip()
        if not lien:
            sans_lien += 1
            continue
        items.append(
            {
                "id": identifiant(source, lien),
                "source": source,
                "lien": lien,
                "titre": _texte(entree.get("title")),
                "resume": nettoyer_extrait(entree.get("summary")) or None,
                "publie_le": _date_iso(entree),
                "recupere_le": recupere_le.isoformat(),
                "rubrique": _rubrique(entree, lien),
                "payload": _payload(entree),
            }
        )
    return items, sans_lien
