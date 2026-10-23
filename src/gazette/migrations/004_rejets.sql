-- Table rejets
CREATE TABLE IF NOT EXISTS rejets (
    id BIGSERIAL PRIMARY KEY,
    brut_id TEXT NOT NULL,           -- Référence vers l'item brut (pas articles_propres !)
    source_id TEXT NOT NULL REFERENCES sources (nom),
    passage_id BIGINT NOT NULL REFERENCES passages (id),
    regle_id TEXT NOT NULL,          -- R01, R02, R03...
    motif TEXT NOT NULL,             -- Motif du rejet
    title TEXT,                      -- Pour analyse
    cree_le TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX rejets_source ON rejets (source_id);
CREATE INDEX rejets_passage ON rejets (passage_id);
CREATE INDEX rejets_regle ON rejets (regle_id);
