import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Source:
    nom: str
    type: str
    region: str
    acces: str
    conditions: str
    notes: str


def charger_sources(chemin: Path) -> list[Source]:
    with chemin.open(encoding="utf-8", newline="") as fichier:
        return [Source(**ligne) for ligne in csv.DictReader(fichier)]


def trouver_source(sources: list[Source], nom: str) -> Source:
    for source in sources:
        if source.nom.casefold() == nom.casefold():
            return source
    noms = ", ".join(s.nom for s in sources)
    raise KeyError(f"Source inconnue : {nom}. Sources disponibles : {noms}")
