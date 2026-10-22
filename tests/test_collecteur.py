from conftest import DepotMemoire, lire

from gazette.collecte import nouveau_client
from gazette.collecteur import SEUIL_SOMMEIL, collecter_tout
from gazette.depot import EtatSource
from gazette.stockage import ArticlesBruts

SANS_ATTENTE = {"attentes": (0, 0), "pause": lambda _: None}


def passer(depot, stockage):
    with nouveau_client() as client:
        return collecter_tout(depot, stockage, client, **SANS_ATTENTE)


def test_deux_passages_zero_doublon(serveur, tmp_path):
    url = serveur.router("/flux.xml", (200, lire("liberation.xml"), {}))
    depot = DepotMemoire(EtatSource("Libération", "PQN", url))
    stockage = ArticlesBruts(tmp_path)

    premier = passer(depot, stockage)
    second = passer(depot, stockage)

    assert (premier["recus"], premier["ecrits"], premier["ignores"]) == (3, 3, 0)
    assert (second["recus"], second["ecrits"], second["ignores"]) == (3, 0, 3)
    assert stockage.compter() == {"liberation": 3}
    assert serveur.appels["/flux.xml"] == 2


def test_flux_non_modifie_rien_a_ecrire(serveur, tmp_path):
    url = serveur.router("/flux.xml", (200, lire("liberation.xml"), {"ETag": '"v1"'}))
    depot = DepotMemoire(EtatSource("Libération", "PQN", url))

    passer(depot, ArticlesBruts(tmp_path))
    passer(depot, ArticlesBruts(tmp_path))

    assert [p.statut for p in depot.passages] == ["ok", "non_modifie"]
    assert depot.etats["Libération"].etag == '"v1"'


def test_item_ecrit_tel_que_recu(serveur, tmp_path):
    url = serveur.router("/flux.xml", (200, lire("liberation.xml"), {}))
    stockage = ArticlesBruts(tmp_path)

    passer(DepotMemoire(EtatSource("Libération", "PQN", url)), stockage)

    fichiers = list((tmp_path / "liberation").glob("*.json"))
    assert len(fichiers) == 3
    assert not list(tmp_path.rglob("*.tmp"))


def test_source_en_panne_mise_en_sommeil_au_troisieme_echec(serveur, tmp_path):
    panne = serveur.router("/panne.xml", (503, b"", {}))
    sain = serveur.router("/flux.xml", (200, lire("liberation.xml"), {}))
    depot = DepotMemoire(
        EtatSource("En panne", "PQR", panne), EtatSource("Libération", "PQN", sain)
    )

    bilans = [passer(depot, ArticlesBruts(tmp_path)) for _ in range(SEUIL_SOMMEIL)]

    en_panne = depot.etats["En panne"]
    assert en_panne.actif is False
    assert en_panne.echecs_consecutifs == SEUIL_SOMMEIL
    assert en_panne.derniere_erreur == "HTTP 503"
    assert [b["endormies"] for b in bilans] == [[], [], ["En panne"]]
    assert serveur.appels["/panne.xml"] == SEUIL_SOMMEIL * 3
    assert depot.etats["Libération"].echecs_consecutifs == 0
    assert stockage_vide_pour(tmp_path, "en-panne")


def test_source_en_sommeil_plus_interrogee(serveur, tmp_path):
    panne = serveur.router("/panne.xml", (503, b"", {}))
    depot = DepotMemoire(EtatSource("En panne", "PQR", panne))

    for _ in range(SEUIL_SOMMEIL + 2):
        passer(depot, ArticlesBruts(tmp_path))

    assert serveur.appels["/panne.xml"] == SEUIL_SOMMEIL * 3


def test_une_reussite_remet_les_echecs_a_zero(serveur, tmp_path):
    url = serveur.router(
        "/flux.xml",
        *[(503, b"", {})] * 3,
        (200, lire("liberation.xml"), {}),
    )
    depot = DepotMemoire(EtatSource("Libération", "PQN", url))

    passer(depot, ArticlesBruts(tmp_path))
    assert depot.etats["Libération"].echecs_consecutifs == 1
    passer(depot, ArticlesBruts(tmp_path))
    assert depot.etats["Libération"].echecs_consecutifs == 0


def test_une_source_en_erreur_n_arrete_pas_les_autres(serveur, tmp_path):
    cassee = serveur.router("/casse.xml", (200, b"<html>pas un flux</html>", {}))
    sain = serveur.router("/flux.xml", (200, lire("liberation.xml"), {}))
    depot = DepotMemoire(EtatSource("Cassée", "PQR", cassee), EtatSource("Libération", "PQN", sain))

    bilan = passer(depot, ArticlesBruts(tmp_path))

    assert (bilan["ok"], bilan["echecs"], bilan["ecrits"]) == (1, 1, 3)
    assert depot.etats["Cassée"].derniere_erreur.startswith("flux illisible")


def stockage_vide_pour(racine, dossier):
    return not (racine / dossier).exists()
