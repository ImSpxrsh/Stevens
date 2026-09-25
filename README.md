# Gauge

Gauge finds early-stage New Jersey startups in public records (SEC Form D,
SBIR/STTR awards, NJEDA/CSIT announcements), explains why each one surfaced,
and checks it against New Jersey funding programs.

The repository contains both the Python evidence and program-matching core and
an offline-friendly product demo inside the actual
[PuruVJ/macos-web](https://github.com/PuruVJ/macos-web) Svelte desktop shell.

## Run the app

```bash
make setup    # Python venv (.[dev,ai,api]) + npm ci
make api      # API on http://localhost:8000, docs at /docs, health at /health
make web      # frontend on http://localhost:5173
make jobs     # one pass of the daily ingestion/watch jobs
make check    # lint, tests, golden path, frontend build (what CI runs)
```

Copy `.env.example` to `.env` first. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
for how public records become discoveries and where each part lives:
`gauge/api/` (backend), `gauge/jobs/` (background jobs), and
`demo/src/components/apps/Gauge/` (frontend).

## macOS demo

```bash
npm install
npm run dev
```

Production check:

```bash
npm run check
npm run build
npm run serve
```

Demo path:

1. Start in **Already funded** on the real New Jersey outline and county map.
2. Switch to **All public signals** for the reveal.
3. Search for `Princeton`, `Newark`, `Camden`, `Hoboken`, `Paterson`, `Trenton`,
   `New Brunswick`, `Jersey City`, or `Montclair`.
4. Open a company and walk through its evidence, unknowns, sources, and
   program-match states.
5. Use the sidebar or dock to show Signals, Programs, and Proof.

All company names, records, counts, matching outcomes, and proof metrics in the
demo are fictional. Re-verify official program rules and replace the frozen
demo snapshot before presenting factual claims.

Demo layout:

- `demo/` — copied and adapted macos-web simulator source
- `demo/src/components/apps/Gauge/` — Gauge product UI and mock data
- `demo/src/components/apps/WallpaperApp/Wallpaper.svelte` — custom wallpaper

The simulator retains its upstream MIT license. See
[THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) and
[demo/LICENSE](./demo/LICENSE).

## Python core

The Python package holds the shared domain types and logic used by the
classifier, program rules, review workflow, and pilot validation:

- `gauge/core/` — provenance-aware source records and normalized company models
- `gauge/classifier/` — likely-startup classifier and exclusions
- `gauge/programs/` — program-matching rules
- `gauge/review/` — search, dedupe, linking, and review tools
- `gauge/pilot/` — pilot metrics and reporting

Requires Python 3.12+.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

For LLM-assisted features, install the `ai` extra and copy `.env.example` to
`.env`:

```bash
pip install -e ".[dev,ai]"
```

Python checks:

```bash
pytest
ruff check .
ruff format .
```
