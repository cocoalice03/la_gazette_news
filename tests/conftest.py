import threading
from collections import Counter
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from gazette.depot import EtatSource, Passage

FIXTURES = Path(__file__).parent / "fixtures"


def lire(nom: str) -> bytes:
    return (FIXTURES / nom).read_bytes()


@dataclass
class Route:
    """Réponses successives d'un chemin ; la dernière est répétée."""

    reponses: list[tuple[int, bytes, dict]]
    appels: int = 0

    def suivante(self) -> tuple[int, bytes, dict]:
        reponse = self.reponses[min(self.appels, len(self.reponses) - 1)]
        self.appels += 1
        return reponse


@dataclass
class ServeurLocal:
    url: str
    routes: dict[str, Route] = field(default_factory=dict)
    entetes_recus: list[dict] = field(default_factory=list)
    appels: Counter = field(default_factory=Counter)

    def router(self, chemin: str, *reponses: tuple[int, bytes, dict]) -> str:
        self.routes[chemin] = Route(list(reponses))
        return self.url + chemin


@pytest.fixture
def serveur():
    """Serveur HTTP réel sur 127.0.0.1, pour simuler des éditeurs en bonne ou mauvaise santé."""
    etat = ServeurLocal(url="")

    class Gestionnaire(BaseHTTPRequestHandler):
        def do_GET(self):
            etat.appels[self.path] += 1
            etat.entetes_recus.append({"chemin": self.path, **dict(self.headers)})
            route = etat.routes.get(self.path)
            code, corps, entetes = route.suivante() if route else (404, b"", {})
            if (
                code == 200
                and entetes.get("ETag")
                and self.headers.get("If-None-Match") == entetes["ETag"]
            ):
                code, corps = 304, b""
            self.send_response(code)
            for cle, valeur in entetes.items():
                self.send_header(cle, valeur)
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Gestionnaire)
    etat.url = f"http://127.0.0.1:{httpd.server_address[1]}"
    fil = threading.Thread(target=httpd.serve_forever, daemon=True)
    fil.start()
    yield etat
    httpd.shutdown()
    httpd.server_close()


class DepotMemoire:
    """Même interface que DepotPostgres, en mémoire."""

    def __init__(self, *etats: EtatSource):
        self.etats = {e.nom: e for e in etats}
        self.passages: list[Passage] = []

    def lister(self, actives_seulement: bool = False) -> list[EtatSource]:
        return [e for e in self.etats.values() if e.actif or not actives_seulement]

    def noter_reussite(self, nom, etag, last_modified):
        e = self.etats[nom]
        e.echecs_consecutifs = 0
        e.etag, e.last_modified = etag, last_modified
        e.derniere_erreur = None
        e.derniere_reussite = "maintenant"

    def noter_echec(self, nom, erreur, seuil):
        e = self.etats[nom]
        e.echecs_consecutifs += 1
        e.derniere_erreur = erreur
        e.actif = e.echecs_consecutifs < seuil
        return not e.actif

    def noter_passage(self, passage):
        self.passages.append(passage)
