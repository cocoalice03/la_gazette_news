# La gazette

Projet M2Ops (EFREI, M2 Data Engineering, groupe M2-DE3, équipe CGMV).

Chaque matin, un pipeline lit les flux RSS de la presse quotidienne régionale (PQR) et nationale (PQN), ne garde que les titres, extraits, liens, dates et rubriques, regroupe les articles par thèmes et publie l'édition de 7 h. Le cadrage est dans [docs/cadrage.md](docs/cadrage.md), les sources dans [sources.csv](sources.csv).

## Prérequis

Git et Docker (avec Docker Compose v2), 4 Go de mémoire pour Docker. Sous Windows, lancer les scripts depuis Git Bash ou WSL.

## Lancer le projet

```sh
git clone https://github.com/cocoalice03/la_gazette_news.git && cd la_gazette_news
bin/dev
```

`bin/dev` crée `.env` à partir de `.env.example` s'il n'existe pas. Il construit les images puis démarre PostgreSQL et Airflow en arrière-plan.

Le DAG `collecte_flux` lit alors toutes les sources actives toutes les 30 minutes. Il écrit chaque nouvel item dans `data/articles_bruts/<source>/<id>.json`.

| Pour | Faire |
|---|---|
| Suivre les exécutions | http://localhost:8080 |
| Voir l'état des sources | `bin/etat` |
| Lancer un passage sans attendre | `docker compose run --rm collecte` |
| Tout arrêter | `docker compose down` |

Le fonctionnement de la collecte (politesse, reprise, mise en sommeil, journaux) est décrit dans [docs/exploitation.md](docs/exploitation.md), les champs stockés dans [docs/donnees.md](docs/donnees.md).

## Tester

```sh
bin/test
```

Construit l'étape `test` du Dockerfile et démarre un PostgreSQL jetable. Lance ensuite `ruff check`, `ruff format --check` et `pytest`.

Les tests n'appellent pas Internet. Ils utilisent les flux enregistrés dans `tests/fixtures/` et un serveur HTTP local qui simule les éditeurs, y compris en panne.

Sans Docker, les tests PostgreSQL sont ignorés, sauf si `GAZETTE_DSN_TEST` est défini :

```sh
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check . && pytest
```

## Arborescence

| Chemin | Contenu |
|---|---|
| `src/gazette/` | Code du pipeline : `collecte.py` (lecture d'un flux), `collecteur.py` (passage sur toutes les sources), `stockage.py` (articles bruts), `depot.py` (état des sources), `migrations/` (SQL versionné) |
| `dags/` | DAG Airflow |
| `tests/` | Tests et flux enregistrés (`fixtures/`) |
| `docs/` | Cadrage, CI/CD, données, exploitation, qualité |
| `infra/` | Description de l'infrastructure |
| `bin/` | `dev`, `test`, `etat` |
| `.github/workflows/ci.yml` | Lint, tests, construction et publication de l'image |

## Image

Chaque push sur `main` publie `ghcr.io/cocoalice03/la_gazette_news:<AAAAMMJJHHMMSS>-<sha>` (et `latest`). Voir [docs/ci-cd.md](docs/ci-cd.md).

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md).
