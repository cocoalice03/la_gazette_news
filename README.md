# La gazette

Projet M2Ops (EFREI, M2 Data Engineering, groupe M2-DE3, équipe CGMV).

Chaque matin, un pipeline lit les flux RSS de la presse quotidienne régionale (PQR) et nationale (PQN), ne garde que les titres, extraits, liens, dates et rubriques, regroupe les articles par thèmes et publie l'édition de 7 h. Le cadrage est dans [docs/cadrage.md](docs/cadrage.md), les sources dans [sources.csv](sources.csv).

## Prérequis

Git et Docker (avec Docker Compose v2). Sous Windows, lancer les scripts depuis Git Bash ou WSL.

## Lancer le projet

```sh
git clone https://github.com/cocoalice03/la_gazette_news.git && cd la_gazette_news
bin/dev
```

`bin/dev` crée `.env` à partir de `.env.example` s'il n'existe pas, construit l'image et démarre PostgreSQL puis la collecte. La collecte lit la source `Libération` et écrit ses items dans `data/brut/<source>-<horodatage>.json`.

Pour une autre source de `sources.csv` : `SOURCE="Le Figaro" bin/dev`.

## Tester

```sh
bin/test
```

Construit l'étape `test` du Dockerfile puis lance `ruff check`, `ruff format --check` et `pytest`. Les tests n'appellent pas le réseau : ils utilisent les flux enregistrés dans `tests/fixtures/`.

Sans Docker :

```sh
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check . && pytest
```

## Arborescence

| Chemin | Contenu |
|---|---|
| `src/gazette/` | Code du pipeline (`collecte.py` : lecture d'un flux, écriture JSON) |
| `tests/` | Tests unitaires et flux enregistrés (`fixtures/`) |
| `docs/` | Cadrage, stratégie CI/CD, puis documentation de chaque TD |
| `infra/` | Description de l'infrastructure (à partir du TD 3) |
| `bin/` | `dev` et `test` |
| `.github/workflows/ci.yml` | Lint, tests, construction et publication de l'image |

## Image

Chaque push sur `main` publie `ghcr.io/cocoalice03/la_gazette_news:<AAAAMMJJHHMMSS>-<sha>` (et `latest`). Voir [docs/ci-cd.md](docs/ci-cd.md).

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md).
