-- Table articles_propres
CREATE TABLE IF NOT EXISTS articles_propres (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources (nom),
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    recupere_le TIMESTAMPTZ NOT NULL,
    category_slug TEXT,
    brut_id TEXT NOT NULL,           -- Référence vers l'item brut
    passage_id BIGINT NOT NULL,      -- Référence passages.id
    cree_le TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX articles_propres_source ON articles_propres (source_id);
CREATE INDEX articles_propres_published_at ON articles_propres (published_at);
CREATE INDEX articles_propres_passage ON articles_propres (passage_id);
