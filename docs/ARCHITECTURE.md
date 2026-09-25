# Gauge architecture

How a public record becomes a startup discovery, and where each piece lives.

## Stack

| Layer | Choice | Where |
|---|---|---|
| Core logic | Python 3.12, standard library only | `gauge/` |
| API | FastAPI + Uvicorn | `gauge/api/` |
| Database | SQLite locally and in the demo; the SQL is kept portable to Postgres | `gauge/db/` |
| Background jobs | Plain Python jobs run by `python -m gauge.jobs`, scheduled by cron or GitHub Actions | `gauge/jobs/` |
| LLM features | Anthropic SDK (`claude-opus-5`), optional `ai` extra | `gauge/ai/` |
| Frontend | Svelte 5 + Vite inside the macOS-style demo shell | `demo/src/components/apps/Gauge/` |

Pure-Python logic has no web or database imports, so the classifier, program
rules, and validation run the same in tests, jobs, and the API.

## Data flow

```
public source ──fetch──▶ raw payload ──parse/normalize──▶ NormalizedRecord (+ Provenance)
   (SEC, SBIR.gov,        data/local/raw/                    gauge/sources/
    NJEDA/CSIT, USPTO)                                                │
                                                                      ▼
                                    link + merge ──▶ CompanyProfile ──┬──▶ review queue (fuzzy / LLM)
                                    gauge/review/                     │     gauge/review/, gauge/ai/
                                                                      ▼
            classify (facts → features → label) ──▶ discovery ──▶ program rules ──▶ evidence card
            gauge/classifier/                                      gauge/programs/    gauge/evidence/
                                                                      │
                                                   new records ──▶ alert gate ──▶ alert feed
                                                                   gauge/review/gate.py  gauge/alerts/
```

`gauge/pipeline.py` runs this whole chain in memory; the database stores its
inputs and outputs so the API and UI can read them.

## Core entities

| Entity | Type | Notes |
|---|---|---|
| Source record | `NormalizedRecord` + `Provenance` | One per filing, award, trademark, or announcement. Provenance (source type, id, URL, date) is required. |
| Company profile | `CompanyProfile` | Many source records per company. Links are auditable (`RecordLink.basis`). |
| Evidence item | `EvidenceItem` | `fact` (cites a record), `inferred` (a Gauge label), or `unknown` (a gap). |
| Program match | `ProgramMatch` | Strong / potential (verify) / not a match, with each criterion's check and source. |
| Alert | `Alert` | Deduplicated by type, company, and record; identity decides whether it is ready or held. |
| Review item | `ReviewItem` | Fuzzy matches, duplicate companies, and low-confidence extractions, with an append-only decision log. |
| Validation run | backtest, precision, and coverage reports | `gauge/validation/`, results in `docs/validation/results/`. |

## Facts, inferences, and AI output stay separate

- **Facts** come only from public records and always carry provenance.
- **Inferred labels** (startup classification, program matches, sectors) are
  derived by code, name their model or rules version, and explain themselves.
- **AI output** (match review, announcement extraction, sector labels) is
  stored with the model, request id, prompt version, and the exact evidence
  sent. It never overrides SEC company ID matching, never clears an alert on
  its own, and low-confidence output goes to the review queue.

## Where data lives

| Data | Location |
|---|---|
| Raw downloads (Form D zips, SBIR CSV, EDGAR XML) | `data/local/raw/` (git-ignored) |
| Normalized records, profiles, derived outputs | SQLite at `GAUGE_DB_PATH` (default `data/local/gauge.sqlite3`) |
| Review decisions, alert statuses | database tables (JSON files for CLI use) |
| Frozen demo snapshot | `fixtures/golden/`, `demo/public/snapshot.json` |
| Validation results | `docs/validation/results/` |

## Configuration

Environment variables, documented in `.env.example`: data and database
paths, `GAUGE_DEMO_MODE` (serve the frozen snapshot, no network),
`SEC_USER_AGENT` (required by SEC for automated access), the USPTO feature
flag, CORS origins, and the Anthropic model and key. No secret has a default,
and none is committed.

## Running it

```bash
make setup    # Python venv + frontend dependencies
make api      # API on :8000, interactive docs at /docs
make web      # frontend on :5173
make jobs     # one pass of the daily jobs
make check    # everything CI runs
```
