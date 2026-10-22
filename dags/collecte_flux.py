"""Collecte de toutes les sources actives, toutes les 30 minutes.

Un passage est idempotent : relancer une exécution ne crée aucun doublon.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from airflow.sdk import dag, task


@dag(
    dag_id="collecte_flux",
    schedule="*/30 * * * *",
    start_date=datetime(2026, 10, 22, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=25),
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    tags=["collecte"],
)
def collecte_flux():
    @task
    def collecter() -> dict:
        from gazette.collecteur import executer
        from gazette.depot import dsn_depuis_environnement
        from gazette.journal import configurer

        configurer()
        return executer(
            dsn_depuis_environnement(),
            Path(os.environ["GAZETTE_SOURCES"]),
            Path(os.environ["GAZETTE_ARTICLES_BRUTS"]),
        )

    @task(retries=0)
    def signaler_sommeil(bilan: dict) -> None:
        """Échoue, donc rougit l'exécution dans Airflow, si une source vient de s'endormir."""
        if bilan["endormies"]:
            raise RuntimeError(
                "Source(s) mise(s) en sommeil après 3 échecs : " + ", ".join(bilan["endormies"])
            )

    signaler_sommeil(collecter())


collecte_flux()
