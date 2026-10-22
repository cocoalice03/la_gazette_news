"""Migrations versionnées : un fichier NNN_nom.sql par version, appliqué une seule fois."""

import sys
from importlib.resources import files

import psycopg

from gazette.journal import configurer, tracer

_VERROU = 74_150_001


def fichiers() -> list[tuple[str, str]]:
    dossier = files(__package__)
    sql = sorted(f for f in dossier.iterdir() if f.name.endswith(".sql"))
    return [(f.name.removesuffix(".sql"), f.read_text(encoding="utf-8")) for f in sql]


def appliquer(connexion: psycopg.Connection) -> list[str]:
    """Applique les migrations manquantes et retourne leurs versions."""
    appliquees = []
    with connexion.transaction():
        connexion.execute("SELECT pg_advisory_xact_lock(%s)", (_VERROU,))
        connexion.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version text PRIMARY KEY,"
            " appliquee_le timestamptz NOT NULL DEFAULT now())"
        )
        deja = {v for (v,) in connexion.execute("SELECT version FROM schema_migrations")}
        for version, sql in fichiers():
            if version in deja:
                continue
            connexion.execute(sql)
            connexion.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            appliquees.append(version)
    for version in appliquees:
        tracer("migration_appliquee", version=version)
    return appliquees


def main() -> int:
    from gazette.depot import dsn_depuis_environnement

    configurer()
    with psycopg.connect(dsn_depuis_environnement(), autocommit=True) as connexion:
        appliquer(connexion)
    return 0


if __name__ == "__main__":
    sys.exit(main())
