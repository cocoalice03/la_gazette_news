CREATE TABLE passages (
    id          bigserial PRIMARY KEY,
    source      text NOT NULL REFERENCES sources (nom),
    debut       timestamptz NOT NULL,
    duree_ms    integer NOT NULL,
    statut      text NOT NULL CHECK (statut IN ('ok', 'non_modifie', 'echec')),
    code_http   integer,
    recus       integer NOT NULL DEFAULT 0,
    ecrits      integer NOT NULL DEFAULT 0,
    ignores     integer NOT NULL DEFAULT 0,
    erreur      text
);

CREATE INDEX passages_source_debut ON passages (source, debut);
