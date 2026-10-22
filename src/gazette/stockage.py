"""Stockage brut : un fichier JSON par item, articles_bruts/<source>/<id>.json.

L'id dérive de (source, lien) : un item déjà écrit n'est jamais réécrit.
"""

import json
import os
import re
import unicodedata
from pathlib import Path


def slug(texte: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")


class ArticlesBruts:
    def __init__(self, racine: Path):
        self.racine = racine

    def chemin(self, item: dict) -> Path:
        return self.racine / slug(item["source"]) / f"{item['id']}.json"

    def ecrire(self, item: dict) -> bool:
        """Écrit l'item s'il est nouveau. Retourne False s'il existait déjà."""
        chemin = self.chemin(item)
        if chemin.exists():
            return False
        chemin.parent.mkdir(parents=True, exist_ok=True)
        provisoire = chemin.with_suffix(f".{os.getpid()}.tmp")
        provisoire.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(provisoire, chemin)
        return True

    def compter(self) -> dict[str, int]:
        if not self.racine.exists():
            return {}
        return {
            dossier.name: sum(1 for _ in dossier.glob("*.json"))
            for dossier in sorted(self.racine.iterdir())
            if dossier.is_dir()
        }
