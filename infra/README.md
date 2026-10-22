# Infrastructure

L'environnement de développement est décrit par `docker-compose.yml` à la racine du dépôt :

| Service | Rôle |
|---|---|
| `postgres` | PostgreSQL 16 : base `gazette` (tables `sources`, `passages`) et base `airflow` (métadonnées d'Airflow) |
| `airflow-init` | Crée la base `airflow` si elle manque, applique les migrations d'Airflow, puis s'arrête |
| `airflow-apiserver` | Interface et API d'Airflow, sur `127.0.0.1:8080` |
| `airflow-scheduler` | Déclenche le DAG `collecte_flux` toutes les 30 minutes et exécute ses tâches |
| `airflow-dag-processor` | Lit les DAG du dossier `dags/` |
| `collecte` | Profil `outils` : un passage de collecte à la main (`docker compose run --rm collecte`) |
| `tests` | Profil `test` : lint et tests avec un PostgreSQL jetable (`bin/test`) |

L'image Airflow est l'étape `airflow` du `Dockerfile` : l'image officielle `apache/airflow:3.2.2-python3.12` avec le paquet `gazette` installé.

Les articles bruts sont écrits dans `data/articles_bruts/`, monté dans les conteneurs. MinIO, Prometheus et Grafana (TD 8) et le déploiement sur le serveur fourni seront décrits dans ce dossier.
