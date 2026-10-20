import json
from pathlib import Path

import httpx
import pytest

from gazette import collecte
from gazette.collecte import LONGUEUR_MAX_EXTRAIT, nettoyer_extrait, parser_flux
from gazette.sources import charger_sources, trouver_source

FIXTURES = Path(__file__).parent / "fixtures"
RACINE = Path(__file__).parent.parent
CHAMPS = {"source", "titre", "lien", "date_publication", "extrait", "rubrique", "guid"}


def lire(nom: str) -> bytes:
    return (FIXTURES / nom).read_bytes()


def test_flux_liberation_donne_trois_items_complets():
    items, ecartes = parser_flux(lire("liberation.xml"), "Libération")

    assert ecartes == 0
    assert len(items) == 3
    for item in items:
        assert set(item) == CHAMPS
        assert item["titre"]
        assert item["lien"].startswith("https://www.liberation.fr/")
        assert item["date_publication"].endswith("+00:00")


def test_auteur_jamais_conserve():
    items, _ = parser_flux(lire("liberation.xml"), "Libération")

    assert all("auteur" not in item and "creator" not in item for item in items)


def test_rubrique_deduite_du_lien_si_absente_du_flux():
    items, _ = parser_flux(lire("liberation.xml"), "Libération")

    assert items[0]["rubrique"] == "environnement"


def test_items_incomplets_ecartes():
    items, ecartes = parser_flux(lire("flux_incomplet.xml"), "Test")

    assert ecartes == 3
    assert [i["titre"] for i in items] == [
        "Article complet avec du HTML dans l'extrait",
        "Article avec un long extrait",
    ]


def test_date_convertie_en_utc():
    items, _ = parser_flux(lire("flux_incomplet.xml"), "Test")

    assert items[0]["date_publication"] == "2026-10-20T06:30:00+00:00"


def test_categorie_du_flux_prioritaire():
    items, _ = parser_flux(lire("flux_incomplet.xml"), "Test")

    assert items[0]["rubrique"] == "Politique"


def test_extrait_sans_html():
    items, _ = parser_flux(lire("flux_incomplet.xml"), "Test")

    assert items[0]["extrait"] == "Un extrait avec des balises"


def test_extrait_tronque():
    extrait = nettoyer_extrait("mot " * 200)

    assert len(extrait) <= LONGUEUR_MAX_EXTRAIT + 1
    assert extrait.endswith("…")


def test_extrait_vide():
    assert nettoyer_extrait(None) == ""


def test_sources_csv_lisible():
    sources = charger_sources(RACINE / "sources.csv")

    assert {s.type for s in sources} == {"PQR", "PQN"}
    assert trouver_source(sources, "libération").acces.startswith("https://")


def test_source_inconnue():
    with pytest.raises(KeyError):
        trouver_source(charger_sources(RACINE / "sources.csv"), "Inconnu")


def test_collecte_bout_en_bout_sans_reseau(tmp_path, monkeypatch):
    def repondre(requete: httpx.Request) -> httpx.Response:
        if requete.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /admin/\n")
        return httpx.Response(200, content=lire("liberation.xml"))

    client_original = httpx.Client

    def client_simule(**kwargs):
        return client_original(transport=httpx.MockTransport(repondre), **kwargs)

    monkeypatch.setattr(collecte.httpx, "Client", client_simule)

    fichier = collecte.collecter("Libération", RACINE / "sources.csv", tmp_path)

    items = json.loads(fichier.read_text(encoding="utf-8"))
    assert len(items) == 3
    assert all(item["recupere_le"] for item in items)


def test_collecte_refusee_par_robots(tmp_path, monkeypatch):
    def repondre(requete: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="User-agent: *\nDisallow: /\n")

    client_original = httpx.Client

    def client_simule(**kwargs):
        return client_original(transport=httpx.MockTransport(repondre), **kwargs)

    monkeypatch.setattr(collecte.httpx, "Client", client_simule)

    with pytest.raises(PermissionError):
        collecte.collecter("Libération", RACINE / "sources.csv", tmp_path)
