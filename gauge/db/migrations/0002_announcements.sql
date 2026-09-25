-- NJEDA / CSIT announcements (#14) and what was extracted from them (#17).

CREATE TABLE announcements (
    id              INTEGER PRIMARY KEY,
    source_type     TEXT NOT NULL CHECK (source_type IN ('njeda_announcement', 'csit_announcement')),
    post_id         TEXT NOT NULL,
    url             TEXT NOT NULL,
    published_on    TEXT NOT NULL,
    title           TEXT NOT NULL,
    text            TEXT NOT NULL,
    fetched_at      TEXT NOT NULL,
    relevant        INTEGER NOT NULL,              -- mentions awards, grants, investments, credits
    extraction_status TEXT NOT NULL CHECK (extraction_status IN
                        ('not_relevant', 'pending', 'extracted', 'failed', 'llm_disabled')),
    extraction_error TEXT,
    extracted_at    TEXT,
    UNIQUE (source_type, post_id)
);
CREATE INDEX ix_announcements_status ON announcements (extraction_status, published_on);

CREATE TABLE announcement_extractions (
    announcement_id INTEGER NOT NULL REFERENCES announcements (id) ON DELETE CASCADE,
    extraction_id   TEXT NOT NULL,
    company_name    TEXT NOT NULL,
    program_name    TEXT,
    award_date      TEXT,
    amount_usd      REAL,
    sector          TEXT,
    town            TEXT,
    quote           TEXT NOT NULL,
    confidence      REAL NOT NULL,
    extracted_by    TEXT NOT NULL,
    needs_review    INTEGER NOT NULL,
    PRIMARY KEY (announcement_id, extraction_id)
);

CREATE TABLE announcement_extraction_issues (
    announcement_id INTEGER NOT NULL,
    extraction_id   TEXT NOT NULL,
    position        INTEGER NOT NULL,
    issue           TEXT NOT NULL,
    PRIMARY KEY (announcement_id, extraction_id, position),
    FOREIGN KEY (announcement_id, extraction_id)
        REFERENCES announcement_extractions (announcement_id, extraction_id) ON DELETE CASCADE
);
