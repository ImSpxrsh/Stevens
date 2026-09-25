-- Gauge initial schema. Written for SQLite; kept to portable SQL so it maps
-- onto Postgres (INTEGER PRIMARY KEY -> BIGSERIAL, TEXT dates -> DATE/TIMESTAMPTZ).
-- Dates are ISO-8601 text. Booleans are 0/1 integers.

-- Ingestion ---------------------------------------------------------------

CREATE TABLE importer_runs (
    id              INTEGER PRIMARY KEY,
    source_type     TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL CHECK (status IN ('running', 'ok', 'failed')),
    records_seen    INTEGER NOT NULL DEFAULT 0,
    records_added   INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    error           TEXT
);
CREATE INDEX ix_importer_runs_source ON importer_runs (source_type, started_at);

-- Raw payloads stay on disk; the table records what was fetched and its hash.
CREATE TABLE raw_source_records (
    id              INTEGER PRIMARY KEY,
    source_type     TEXT NOT NULL,
    source_id       TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    fetched_at      TEXT NOT NULL,
    content_sha256  TEXT NOT NULL,
    storage_path    TEXT,
    importer_run_id INTEGER REFERENCES importer_runs (id),
    UNIQUE (source_type, source_id)
);

-- Normalized public records, one row per filing / award / announcement.
CREATE TABLE source_records (
    id              INTEGER PRIMARY KEY,
    record_key      TEXT NOT NULL UNIQUE,          -- "<source_type>:<source_id>"
    source_type     TEXT NOT NULL,
    source_id       TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    source_date     TEXT NOT NULL,
    name            TEXT NOT NULL,
    name_normalized TEXT NOT NULL,
    cik             TEXT,
    street          TEXT,
    city            TEXT,
    state           TEXT,
    postal_code     TEXT,
    county          TEXT,
    latitude        REAL,
    longitude       REAL,
    importer_run_id INTEGER REFERENCES importer_runs (id),
    UNIQUE (source_type, source_id)
);
CREATE INDEX ix_source_records_name ON source_records (name_normalized);
CREATE INDEX ix_source_records_cik ON source_records (cik);
CREATE INDEX ix_source_records_city ON source_records (city);
CREATE INDEX ix_source_records_date ON source_records (source_date);

CREATE TABLE form_d_facts (
    record_id       INTEGER PRIMARY KEY REFERENCES source_records (id) ON DELETE CASCADE,
    industry_group  TEXT,
    is_pooled_investment_fund INTEGER NOT NULL DEFAULT 0,
    entity_type     TEXT,
    jurisdiction_of_incorporation TEXT,
    year_of_incorporation INTEGER,
    incorporated_within_five_years INTEGER,
    revenue_range   TEXT,
    total_offering_amount REAL,
    total_amount_sold REAL,
    date_of_first_sale TEXT,
    is_amendment    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE form_d_securities (
    record_id       INTEGER NOT NULL REFERENCES source_records (id) ON DELETE CASCADE,
    position        INTEGER NOT NULL,
    security        TEXT NOT NULL,
    PRIMARY KEY (record_id, position)
);

CREATE TABLE sbir_facts (
    record_id       INTEGER PRIMARY KEY REFERENCES source_records (id) ON DELETE CASCADE,
    phase           TEXT NOT NULL,
    program         TEXT NOT NULL,
    agency          TEXT,
    award_amount    REAL,
    award_start     TEXT,
    award_end       TEXT,
    topic_title     TEXT,
    abstract        TEXT,
    employee_count  INTEGER,
    place_of_performance_state TEXT
);

-- Companies and derived outputs --------------------------------------------

CREATE TABLE companies (
    id              TEXT PRIMARY KEY,               -- "cik:..." or "rec:..."
    name            TEXT NOT NULL,
    name_normalized TEXT NOT NULL,
    town            TEXT,
    county          TEXT,
    state           TEXT,
    latitude        REAL,
    longitude       REAL,
    sector          TEXT,
    first_seen      TEXT,
    last_seen       TEXT,
    startup_label   TEXT CHECK (startup_label IN ('likely_startup', 'not_startup', 'uncertain')),
    startup_probability REAL,
    startup_confidence REAL,
    exclusion_reason TEXT,
    exclusion_explanation TEXT,
    model_version   TEXT,
    as_of           TEXT,
    updated_at      TEXT NOT NULL
);
CREATE INDEX ix_companies_name ON companies (name_normalized);
CREATE INDEX ix_companies_town ON companies (town);
CREATE INDEX ix_companies_county ON companies (county);
CREATE INDEX ix_companies_sector ON companies (sector);
CREATE INDEX ix_companies_label ON companies (startup_label, startup_probability);

-- How each record came to belong to its company (auditable merges).
CREATE TABLE company_source_links (
    record_id       INTEGER PRIMARY KEY REFERENCES source_records (id) ON DELETE CASCADE,
    company_id      TEXT NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    basis           TEXT NOT NULL CHECK (basis IN
                        ('exact_cik', 'exact_name_postal', 'human_approved', 'model_approved', 'new_company')),
    review_item_id  TEXT,
    linked_at       TEXT NOT NULL
);
CREATE INDEX ix_links_company ON company_source_links (company_id);

CREATE TABLE classification_features (
    company_id      TEXT NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    position        INTEGER NOT NULL,
    feature         TEXT NOT NULL,
    description     TEXT NOT NULL,
    contribution    REAL NOT NULL,
    PRIMARY KEY (company_id, position)
);

CREATE TABLE evidence_items (
    company_id      TEXT NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    position        INTEGER NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('fact', 'inferred', 'unknown')),
    claim           TEXT NOT NULL,
    value           TEXT,
    confidence      REAL,
    limitations     TEXT,
    extracted_by    TEXT,
    source_type     TEXT,
    source_id       TEXT,
    source_url      TEXT,
    source_date     TEXT,
    PRIMARY KEY (company_id, position),
    CHECK (kind <> 'fact' OR source_url IS NOT NULL)
);

CREATE TABLE program_matches (
    company_id      TEXT NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    program_id      TEXT NOT NULL,
    program_name    TEXT NOT NULL,
    result          TEXT NOT NULL CHECK (result IN ('strong_match', 'potential_match_verify', 'not_a_match')),
    summary         TEXT NOT NULL,
    rules_version   TEXT NOT NULL,
    as_of           TEXT NOT NULL,
    PRIMARY KEY (company_id, program_id)
);
CREATE INDEX ix_program_matches_result ON program_matches (program_id, result);

CREATE TABLE program_match_checks (
    company_id      TEXT NOT NULL,
    program_id      TEXT NOT NULL,
    position        INTEGER NOT NULL,
    criterion_id    TEXT NOT NULL,
    criterion_text  TEXT NOT NULL,
    basis           TEXT NOT NULL CHECK (basis IN ('screened', 'attested')),
    outcome         TEXT CHECK (outcome IN ('pass', 'fail', 'unknown')),  -- NULL for attested
    explanation     TEXT,
    needs_confirmation INTEGER NOT NULL DEFAULT 0,
    verification_question TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    PRIMARY KEY (company_id, program_id, position),
    FOREIGN KEY (company_id, program_id) REFERENCES program_matches (company_id, program_id) ON DELETE CASCADE
);

CREATE TABLE program_match_check_evidence (
    company_id      TEXT NOT NULL,
    program_id      TEXT NOT NULL,
    position        INTEGER NOT NULL,
    record_key      TEXT NOT NULL,
    PRIMARY KEY (company_id, program_id, position, record_key),
    FOREIGN KEY (company_id, program_id, position)
        REFERENCES program_match_checks (company_id, program_id, position) ON DELETE CASCADE
);

-- Review queue ------------------------------------------------------------

CREATE TABLE review_items (
    id              TEXT PRIMARY KEY,
    kind            TEXT NOT NULL CHECK (kind IN ('record_match', 'duplicate_companies', 'extraction')),
    subject         TEXT NOT NULL,
    candidate_company_id TEXT NOT NULL,
    score           REAL NOT NULL,
    created_at      TEXT NOT NULL,
    UNIQUE (kind, subject, candidate_company_id)
);

CREATE TABLE review_item_reasons (
    review_item_id  TEXT NOT NULL REFERENCES review_items (id) ON DELETE CASCADE,
    position        INTEGER NOT NULL,
    reason          TEXT NOT NULL,
    PRIMARY KEY (review_item_id, position)
);

CREATE TABLE review_item_evidence (
    review_item_id  TEXT NOT NULL REFERENCES review_items (id) ON DELETE CASCADE,
    position        INTEGER NOT NULL,
    source_type     TEXT NOT NULL,
    source_id       TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    source_date     TEXT NOT NULL,
    PRIMARY KEY (review_item_id, position)
);

-- Append-only: rows are never updated or deleted.
CREATE TABLE review_decisions (
    id              INTEGER PRIMARY KEY,
    review_item_id  TEXT NOT NULL REFERENCES review_items (id),
    action          TEXT NOT NULL CHECK (action IN
                        ('approve_merge', 'reject_merge', 'leave_uncertain', 'annotate')),
    actor           TEXT NOT NULL,
    actor_type      TEXT NOT NULL CHECK (actor_type IN ('human', 'model', 'system')),
    decided_at      TEXT NOT NULL,
    note            TEXT NOT NULL DEFAULT '',
    details_json    TEXT NOT NULL DEFAULT '{}'   -- audit metadata (model, request id, evidence sent)
);
CREATE INDEX ix_review_decisions_item ON review_decisions (review_item_id, id);

CREATE TRIGGER review_decisions_no_update BEFORE UPDATE ON review_decisions
BEGIN SELECT RAISE(ABORT, 'review decisions are append-only'); END;
CREATE TRIGGER review_decisions_no_delete BEFORE DELETE ON review_decisions
BEGIN SELECT RAISE(ABORT, 'review decisions are append-only'); END;

-- Alerts ------------------------------------------------------------------

CREATE TABLE alerts (
    id              TEXT PRIMARY KEY,
    type            TEXT NOT NULL CHECK (type IN
                        ('new_likely_startup', 'raised_again', 'phase_ii_win', 'sector_spike')),
    company_id      TEXT NOT NULL,
    company_name    TEXT NOT NULL,
    record_key      TEXT NOT NULL,
    summary         TEXT NOT NULL,
    why             TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    source_date     TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('ready', 'held', 'sent', 'dismissed')),
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    UNIQUE (type, company_id, record_key)
);
CREATE INDEX ix_alerts_feed ON alerts (status, source_date);
CREATE INDEX ix_alerts_company ON alerts (company_id);

-- Validation ----------------------------------------------------------------

CREATE TABLE validation_runs (
    id              INTEGER PRIMARY KEY,
    kind            TEXT NOT NULL CHECK (kind IN ('backtest', 'precision', 'coverage')),
    run_at          TEXT NOT NULL,
    as_of           TEXT NOT NULL,
    headline        TEXT NOT NULL,
    report_path     TEXT
);

CREATE TABLE validation_run_parameters (
    run_id          INTEGER NOT NULL REFERENCES validation_runs (id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    value           TEXT NOT NULL,
    PRIMARY KEY (run_id, name)
);
