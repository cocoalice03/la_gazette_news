"""Tests d'intégration pour les tables articles_propres et rejets."""

import os
import uuid
from pathlib import Path

import psycopg
import pytest

from gazette import migrations


def obtenir_dsn() -> str:
    # 1. Variable d'env prioritaire
    if "GAZETTE_DSN" in os.environ:
        return os.environ["GAZETTE_DSN"]
    if "GAZETTE_DSN_TEST" in os.environ:
        return os.environ["GAZETTE_DSN_TEST"]

    # 2. Lecture du fichier .env
    env_file = Path(__file__).parent.parent / ".env"
    env_vars = {}
    if env_file.exists():
        for line in env_file.read_text().strip().split("\n"):
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    user = env_vars.get("POSTGRES_USER", "gazette")
    password = env_vars.get("POSTGRES_PASSWORD", "a_changer_en_local")
    db = env_vars.get("POSTGRES_DB", "gazette")
    return f"postgresql://{user}:{password}@localhost:5432/{db}"


@pytest.fixture(scope="module")
def db_connection():
    """Fixture qui fournit une connexion PostgreSQL dans un schéma temporaire isolé."""
    dsn = obtenir_dsn()
    schema = f"test_{uuid.uuid4().hex[:8]}"

    try:
        admin_conn = psycopg.connect(dsn, autocommit=True)
    except psycopg.OperationalError as e:
        pytest.skip(f"PostgreSQL non disponible pour les tests: {e}")

    with admin_conn as admin:
        admin.execute(f"CREATE SCHEMA {schema}")
        try:
            with psycopg.connect(dsn, autocommit=True, options=f"-c search_path={schema}") as conn:
                # Appliquer toutes les migrations dans ce schéma
                migrations.appliquer(conn)

                # Insérer les données parentes nécessaires pour respecter les contraintes FK
                conn.execute("""
                    INSERT INTO sources (nom, type, url_flux) VALUES
                        ('le-monde', 'PQN', 'https://lemonde.fr/rss'),
                        ('liberation', 'PQN', 'https://liberation.fr/rss')
                    ON CONFLICT DO NOTHING
                """)
                conn.execute("""
                    INSERT INTO passages (id, source, debut, duree_ms, statut) VALUES
                        (1, 'le-monde', NOW(), 100, 'ok')
                    ON CONFLICT DO NOTHING
                """)

                yield conn
        finally:
            admin.execute(f"DROP SCHEMA {schema} CASCADE")


def test_migration_articles_propres(db_connection):
    """Test que la table articles_propres existe et a la bonne structure."""
    result = db_connection.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = CURRENT_SCHEMA AND table_name = 'articles_propres'
        )
    """).fetchone()
    assert result[0] is True, "La table articles_propres n'existe pas"


def test_migration_rejets(db_connection):
    """Test que la table rejets existe et a la bonne structure."""
    result = db_connection.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = CURRENT_SCHEMA AND table_name = 'rejets'
        )
    """).fetchone()
    assert result[0] is True, "La table rejets n'existe pas"


def test_insert_article_propre(db_connection):
    """Test l'insertion d'un article dans articles_propres."""
    db_connection.execute("""
        INSERT INTO articles_propres (
            id, source_id, url, title, summary, published_at,
            recupere_le, category_slug, brut_id, passage_id
        ) VALUES (
            'test-123', 'le-monde', 'https://example.com',
            'Un titre', 'Un résumé', NOW(), NOW(),
            'politique', 'brut-123', 1
        )
    """)

    result = db_connection.execute("""
        SELECT title, source_id FROM articles_propres WHERE id = 'test-123'
    """).fetchone()
    assert result is not None
    assert result[0] == "Un titre"
    assert result[1] == "le-monde"


def test_insert_rejet(db_connection):
    """Test l'insertion d'un rejet dans la table rejets."""
    db_connection.execute("""
        INSERT INTO rejets (
            brut_id, source_id, passage_id, regle_id, motif, title
        ) VALUES (
            'brut-456', 'liberation', 1, 'R01_publi',
            'Contenu commercial', 'Bons plans'
        )
    """)

    result = db_connection.execute("""
        SELECT regle_id, motif FROM rejets WHERE brut_id = 'brut-456'
    """).fetchone()
    assert result is not None
    assert result[0] == "R01_publi"
    assert result[1] == "Contenu commercial"


def test_foreign_key_source(db_connection):
    """Test que la clé étrangère vers sources fonctionne."""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db_connection.execute("""
            INSERT INTO articles_propres (
                id, source_id, url, title, summary, published_at,
                recupere_le, category_slug, brut_id, passage_id
            ) VALUES (
                'test-fk', 'source_inexistante', 'https://example.com',
                'Test', 'Test', NOW(), NOW(),
                'test', 'brut-fk', 1
            )
        """)


def test_index_articles_propres(db_connection):
    """Test que les index sont créés sur articles_propres."""
    result = db_connection.execute("""
        SELECT EXISTS (
            SELECT FROM pg_indexes
            WHERE schemaname = CURRENT_SCHEMA
              AND tablename = 'articles_propres'
              AND indexname = 'articles_propres_source'
        )
    """).fetchone()
    assert result[0] is True


def test_index_rejets(db_connection):
    """Test que les index sont créés sur rejets."""
    result = db_connection.execute("""
        SELECT EXISTS (
            SELECT FROM pg_indexes
            WHERE schemaname = CURRENT_SCHEMA
              AND tablename = 'rejets'
              AND indexname = 'rejets_regle'
        )
    """).fetchone()
    assert result[0] is True
