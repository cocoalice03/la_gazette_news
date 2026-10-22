"""Journaux structurés : une ligne JSON par événement."""

import json
import logging
import sys

journal = logging.getLogger("gazette")


def tracer(evenement: str, niveau: int = logging.INFO, **champs) -> None:
    ligne = {"evenement": evenement, **champs}
    journal.log(niveau, json.dumps(ligne, ensure_ascii=False, default=str))


def configurer() -> None:
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
