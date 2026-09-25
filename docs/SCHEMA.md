# Database schema

Defined in `gauge/db/migrations/0001_initial.sql` and applied by
`python -m gauge.db init`. SQLite locally; the SQL avoids SQLite-only
features except `INSERT OR IGNORE` and triggers, so it ports to Postgres.

```
importer_runs ─┬─< raw_source_records            (what was fetched, content hash)
               └─< source_records ─┬─ form_d_facts ─< form_d_securities
                                   ├─ sbir_facts
                                   └─ company_source_links >─ companies ─┬─< classification_features
                                        (basis: exact_cik | exact_name_postal |       ├─< evidence_items
                                         human_approved | model_approved |            └─< program_matches ─< program_match_checks ─< program_match_check_evidence
                                         new_company; review_item_id)

review_items ─┬─< review_item_reasons            alerts               validation_runs ─< validation_run_parameters
              ├─< review_item_evidence           (dedupe: id and
              └─< review_decisions (append-only)  UNIQUE(type, company_id, record_key))
```

| Table | Holds | Key constraints |
|---|---|---|
| `source_records` | one normalized filing / award / announcement | `UNIQUE (source_type, source_id)`, `record_key` unique |
| `form_d_facts`, `sbir_facts`, `form_d_securities` | source-specific fields as columns, not JSON | one row per record |
| `companies` | canonical company plus its latest classification | derived; replaced on each refresh |
| `company_source_links` | how each record joined its company | `basis` enum, optional `review_item_id` |
| `evidence_items` | fact / inferred / unknown claims, in card order | a `fact` must have a `source_url` (CHECK) |
| `program_matches`, `program_match_checks` | result per program, each criterion's outcome, attested items | `outcome` NULL only for attested criteria |
| `review_items`, `review_decisions` | fuzzy matches, duplicates, extractions, and who decided what | decisions are append-only (triggers) |
| `alerts` | deduplicated alert feed with status | `UNIQUE (type, company_id, record_key)` |
| `importer_runs`, `raw_source_records` | ingestion runs and fetched payload hashes | |
| `validation_runs` | backtest / precision / coverage headlines | |

Indexes cover company search (`name_normalized`), source lookups (`cik`,
`source_id`), town / county / sector filters, labels, and the alert feed
(`status, source_date`).

Derived tables (companies and everything under them) are recomputed from
`source_records` plus `review_decisions` by `gauge.db.refresh.refresh`, so
they never drift from the inputs. Review decisions and alert statuses are
the only human-entered state.

Commands:

```bash
python -m gauge.db init                    # create or migrate
python -m gauge.db seed --fixtures         # golden fixtures, for frontend work
python -m gauge.db seed --records data/local/records_nj.json --as-of 2026-06-30
python -m gauge.db status
```
