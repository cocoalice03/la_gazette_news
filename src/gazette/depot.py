"""État des sources et historique des passages, dans PostgreSQL."""

import os
from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import class_row

from gazette.sources import Source


@dataclass
class EtatSource:
    nom: str
    type: str
    url_flux: str
    actif: bool = True
    derniere_reussite: datetime | None = None
    echecs_consecutifs: int = 0
    etag: str | None = None
    last_modified: str | None = None
    derniere_erreur: str | None = None
    en_sommeil_depuis: datetime | None = None


@dataclass
class Passage:
    source: str
    debut: datetime
    duree_ms: int
    statut: str
    code_http: int | None = None
    recus: int = 0
    ecrits: int = 0
    ignores: int = 0
    erreur: str | None = None


def dsn_depuis_environnement() -> str:
    try:
        return os.environ["GAZETTE_DSN"]
    except KeyError:
        raise RuntimeError("Variable GAZETTE_DSN absente (voir .env.example)") from None


class DepotPostgres:
    def __init__(self, connexion: psycopg.Connection):
        self.connexion = connexion

    def synchroniser(self, sources: list[Source]) -> None:
        """Reporte sources.csv dans la table sans toucher à l'état de collecte.

        Si l'URL d'un flux change, son ETag et son Last-Modified sont oubliés.
        """
        with self.connexion.transaction():
            for source in sources:
                self.connexion.execute(
                    """
                    INSERT INTO sources (nom, type, url_flux) VALUES (%s, %s, %s)
                    ON CONFLICT (nom) DO UPDATE SET
                        type = EXCLUDED.type,
                        url_flux = EXCLUDED.url_flux,
                        etag = CASE WHEN sources.url_flux = EXCLUDED.url_flux
                                    THEN sources.etag END,
                        last_modified = CASE WHEN sources.url_flux = EXCLUDED.url_flux
                                             THEN sources.last_modified END
                    """,
                    (source.nom, source.type, source.acces),
                )

    def lister(self, actives_seulement: bool = False) -> list[EtatSource]:
        filtre = "WHERE actif" if actives_seulement else ""
        with self.connexion.cursor(row_factory=class_row(EtatSource)) as curseur:
            return curseur.execute(f"SELECT * FROM sources {filtre} ORDER BY nom").fetchall()

    def noter_reussite(self, nom: str, etag: str | None, last_modified: str | None) -> None:
        self.connexion.execute(
            """
            UPDATE sources SET derniere_reussite = now(), echecs_consecutifs = 0,
                etag = %s, last_modified = %s, derniere_erreur = NULL
            WHERE nom = %s
            """,
            (etag, last_modified, nom),
        )

    def noter_echec(self, nom: str, erreur: str, seuil: int) -> bool:
        """Incrémente les échecs. Retourne True si la source vient d'être mise en sommeil."""
        (actif,) = self.connexion.execute(
            """
            UPDATE sources SET
                echecs_consecutifs = echecs_consecutifs + 1,
                derniere_erreur = %s,
                actif = echecs_consecutifs + 1 < %s,
                en_sommeil_depuis = CASE WHEN echecs_consecutifs + 1 >= %s THEN now() END
            WHERE nom = %s
            RETURNING actif
            """,
            (erreur, seuil, seuil, nom),
        ).fetchone()
        return not actif

    def reactiver(self, nom: str) -> bool:
        curseur = self.connexion.execute(
            """
            UPDATE sources SET actif = true, echecs_consecutifs = 0, en_sommeil_depuis = NULL
            WHERE nom = %s
            """,
            (nom,),
        )
        return curseur.rowcount == 1

    def noter_passage(self, passage: Passage) -> None:
        self.connexion.execute(
            """
            INSERT INTO passages
                (source, debut, duree_ms, statut, code_http, recus, ecrits, ignores, erreur)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                passage.source,
                passage.debut,
                passage.duree_ms,
                passage.statut,
                passage.code_http,
                passage.recus,
                passage.ecrits,
                passage.ignores,
                passage.erreur,
            ),
        )
