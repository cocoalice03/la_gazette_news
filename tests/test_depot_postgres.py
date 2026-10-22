"""Tests sur un vrai PostgreSQL, dans un schéma jetable. Ignorés sans GAZETTE_DSN_TEST."""

import os
import uuid
from datetime import UTC, datetime

import psycopg
import pytest

from gazette import migrations
from gazette.depot import DepotPostgres, Passage
from gazette.sources import Source

DSN = os.environ.get("GAZETTE_DSN_TEST")
pytestmark = pytest.mark.skipif(not DSN, reason="GAZETTE_DSN_TEST non défini")


def source(nom: str, url: str) -> Source:
    return Source(nom=nom, type="PQN", region="National", acces=url, conditions="", notes="")


@pytest.fixture
def connexion():
    schema = f"test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute(f"CREATE SCHEMA {schema}")
        try:
            with psycopg.connect(
                DSN, autocommit=True, options=f"-c search_path={schema}"
            ) as connexion:
                yield connexion
        finally:
            admin.execute(f"DROP SCHEMA {schema} CASCADE")


def test_migrations_appliquees_une_seule_fois(connexion):
    assert migrations.appliquer(connexion) == ["001_sources", "002_passages"]
    assert migrations.appliquer(connexion) == []


def test_synchronisation_garde_l_etat_et_oublie_l_etag_si_l_url_change(connexion):
    migrations.appliquer(connexion)
    depot = DepotPostgres(connexion)
    depot.synchroniser([source("Le Monde", "https://a.fr/rss")])
    depot.noter_reussite("Le Monde", '"v1"', None)

    depot.synchroniser([source("Le Monde", "https://a.fr/rss")])
    assert depot.lister()[0].etag == '"v1"'

    depot.synchroniser([source("Le Monde", "https://b.fr/rss")])
    (etat,) = depot.lister()
    assert etat.etag is None
    assert etat.derniere_reussite is not None


def test_sommeil_au_troisieme_echec_puis_reactivation(connexion):
    migrations.appliquer(connexion)
    depot = DepotPostgres(connexion)
    depot.synchroniser([source("Le Monde", "https://a.fr/rss")])

    assert [depot.noter_echec("Le Monde", "HTTP 503", 3) for _ in range(3)] == [
        False,
        False,
        True,
    ]
    (etat,) = depot.lister()
    assert (etat.actif, etat.echecs_consecutifs) == (False, 3)
    assert etat.en_sommeil_depuis is not None
    assert depot.lister(actives_seulement=True) == []

    assert depot.reactiver("Le Monde")
    assert depot.lister(actives_seulement=True)[0].echecs_consecutifs == 0


def test_passage_enregistre(connexion):
    migrations.appliquer(connexion)
    depot = DepotPostgres(connexion)
    depot.synchroniser([source("Le Monde", "https://a.fr/rss")])

    depot.noter_passage(
        Passage("Le Monde", datetime.now(UTC), 120, "ok", 200, recus=50, ecrits=12, ignores=38)
    )

    ligne = connexion.execute("SELECT statut, recus, ecrits, ignores FROM passages").fetchone()
    assert ligne == ("ok", 50, 12, 38)
