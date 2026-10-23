import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from conftest import lire
from gazette.collecte import (
    LONGUEUR_MAX_EXTRAIT,
    ErreurCollecte,
    identifiant,
    items_bruts,
    nettoyer_extrait,
    nouveau_client,
    telecharger,
)
from gazette.sources import charger_sources, trouver_source

RACINE = Path(__file__).parent.parent
MAINTENANT = datetime(2026, 10, 22, 7, 0, tzinfo=UTC)
CHAMPS = {
    "id",
    "source",
    "lien",
    "titre",
    "resume",
    "publie_le",
    "recupere_le",
    "rubrique",
    "payload",
}


def test_flux_liberation_donne_trois_items_complets():
    items, sans_lien = items_bruts(lire("liberation.xml"), "Libération", MAINTENANT)

    assert sans_lien == 0
    assert len(items) == 3
    for item in items:
        assert set(item) == CHAMPS
        assert item["titre"]
        assert item["lien"].startswith("https://www.liberation.fr/")
        assert item["publie_le"].endswith("+00:00")
        assert item["recupere_le"] == "2026-10-22T07:00:00+00:00"
        assert item["id"] == identifiant("Libération", item["lien"])


def test_auteur_jamais_conserve():
    items, _ = items_bruts(lire("liberation.xml"), "Libération", MAINTENANT)

    texte = json.dumps(items, ensure_ascii=False)
    assert "AFP" not in texte
    assert all("author" not in item["payload"] for item in items)


def test_texte_integral_images_et_commentaires_retires():
    (item,), _ = items_bruts(lire("flux_borne.xml"), "Test", MAINTENANT)

    texte = json.dumps(item, ensure_ascii=False)
    assert "texte intégral" not in texte
    assert "photo.jpg" not in texte
    assert "commentaires" not in texte
    assert "Jeanne Martin" not in texte
    assert item["payload"]["title"] == "Article avec tout ce qu'on ne garde pas"


def test_flux_atom_meme_format_que_rss():
    (item,), _ = items_bruts(lire("flux_atom.xml"), "Atom", MAINTENANT)

    assert item["titre"] == "Un article Atom"
    assert item["lien"] == "https://exemple.fr/atom/article"
    assert item["publie_le"] == "2026-10-21T16:00:00+00:00"
    assert item["resume"] == "Le résumé Atom"


def test_rubrique_deduite_du_lien_si_absente_du_flux():
    items, _ = items_bruts(lire("liberation.xml"), "Libération", MAINTENANT)

    assert items[0]["rubrique"] == "environnement"


def test_seuls_les_items_sans_lien_sont_ignores():
    items, sans_lien = items_bruts(lire("flux_incomplet.xml"), "Test", MAINTENANT)

    assert sans_lien == 1
    assert len(items) == 4
    sans_date = next(i for i in items if i["lien"].endswith("article-sans-date"))
    sans_titre = next(i for i in items if i["lien"].endswith("article-sans-titre"))
    assert sans_date["publie_le"] is None
    assert sans_titre["titre"] is None


def test_date_convertie_en_utc():
    items, _ = items_bruts(lire("flux_incomplet.xml"), "Test", MAINTENANT)

    assert items[0]["publie_le"] == "2026-10-20T06:30:00+00:00"


def test_categorie_du_flux_prioritaire():
    items, _ = items_bruts(lire("flux_incomplet.xml"), "Test", MAINTENANT)

    assert items[0]["rubrique"] == "Politique"


def test_resume_sans_html():
    items, _ = items_bruts(lire("flux_incomplet.xml"), "Test", MAINTENANT)

    assert items[0]["resume"] == "Un extrait avec des balises"


def test_extrait_tronque():
    extrait = nettoyer_extrait("mot " * 200)

    assert len(extrait) <= LONGUEUR_MAX_EXTRAIT + 1
    assert extrait.endswith("…")


def test_extrait_vide():
    assert nettoyer_extrait(None) == ""


def test_flux_illisible_est_une_erreur():
    with pytest.raises(ErreurCollecte, match="flux illisible"):
        items_bruts(b"<html><body>Accepter les cookies</body>", "Test", MAINTENANT)


def test_flux_vide_est_une_erreur():
    vide = b'<?xml version="1.0"?><rss version="2.0"><channel><title>Vide</title></channel></rss>'

    with pytest.raises(ErreurCollecte, match="flux vide"):
        items_bruts(vide, "Test", MAINTENANT)


def test_gzip_sans_en_tete_decompresse(serveur):
    url = serveur.router("/flux.xml", (200, gzip.compress(lire("liberation.xml")), {}))

    with nouveau_client() as client:
        telechargement = telecharger(client, url)

    items, _ = items_bruts(telechargement.contenu, "Libération", MAINTENANT)
    assert len(items) == 3


def test_entetes_conditionnels_et_user_agent(serveur):
    url = serveur.router("/flux.xml", (200, lire("liberation.xml"), {"ETag": '"v1"'}))

    with nouveau_client() as client:
        premier = telecharger(client, url)
        second = telecharger(client, url, etag=premier.etag)

    assert premier.code_http == 200
    assert second.code_http == 304
    assert second.contenu is None
    assert serveur.entetes_recus[1]["If-None-Match"] == '"v1"'
    assert serveur.entetes_recus[0]["User-Agent"].startswith("LaGazetteBot/")


def test_erreur_transitoire_reessayee_avec_attente_croissante(serveur):
    url = serveur.router(
        "/flux.xml", (503, b"", {}), (503, b"", {}), (200, lire("liberation.xml"), {})
    )
    attentes = []

    with nouveau_client() as client:
        telechargement = telecharger(client, url, attentes=(2.0, 8.0), pause=attentes.append)

    assert telechargement.code_http == 200
    assert attentes == [2.0, 8.0]


def test_erreur_permanente_non_reessayee(serveur):
    url = serveur.router("/flux.xml", (404, b"", {}))

    with nouveau_client() as client, pytest.raises(ErreurCollecte) as erreur:
        telecharger(client, url, attentes=(0, 0), pause=lambda _: None)

    assert erreur.value.code_http == 404
    assert serveur.appels["/flux.xml"] == 1


def test_sources_csv_lisible():
    sources = charger_sources(RACINE / "sources.csv")

    assert {s.type for s in sources} == {"PQR", "PQN"}
    assert trouver_source(sources, "libération").acces.startswith("https://")


def test_source_inconnue():
    with pytest.raises(KeyError):
        trouver_source(charger_sources(RACINE / "sources.csv"), "Inconnu")
