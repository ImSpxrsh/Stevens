# Gauge

Gauge finds early-stage New Jersey startups in public records (SEC Form D,
SBIR/STTR awards, NJEDA/CSIT announcements), explains why each one surfaced,
and checks it against New Jersey funding programs.

The repository contains both the Python evidence and program-matching core and
**Ivisyx**, an offline-friendly venture-intelligence demo running inside the
[PuruVJ/macos-web](https://github.com/PuruVJ/macos-web) Svelte desktop shell.

## Ivisyx demo

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

What's in the suite:

- **Overview**: thesis matches, KPIs, deal-flow chart, pipeline funnel, agenda and portfolio health.
- **NJ map**: an interactive New Jersey map. Scroll or pinch to zoom, drag to pan, click a county or any of ~220 municipalities to fly in, and zoom far enough to see individual companies. It also has search, layers, a minimap, and a live signal stream.
- **Pipeline**: drag-and-drop kanban and table, owner filters, fit scores.
- **Companies**: ~1,400 companies with search and filters; each synthetic company gets a generated logo.
- **Portfolio**, **Market map**, **Fund & LPs** (TVPI/DPI/IRR, J-curve, LP report generator), **Programs**, **Sources**.
- **Assistant**: scripted memo, portfolio, lookalike and meeting-prep answers. It does not call a language model.
- **⌘K command palette** and a **firm setup** screen. Pick a preset or enter any fund's thesis, stages, geography and brand color, and every fit score re-ranks.

Demo path: Overview → NJ map (zoom into Mercer County, then Princeton) → open a
company → Draft IC memo → Pipeline → Fund & LPs → switch workspace in the sidebar
to show it works for any VC. The default workspace is the fictional 59 Capital.

Data: six real New Jersey company profiles link to official sources and never
receive simulated data. Every other company, deal, metric, fund figure, LP and
signal is synthetic, and town coordinates are approximate. Program names and links
point to official pages; re-verify rules before presenting factual claims.

Layout:

- `demo/` — adapted macos-web simulator source
- `demo/src/components/apps/Ivisyx/` — Ivisyx app (views, overlays, data generators)
- `demo/src/components/apps/WallpaperApp/Wallpaper.svelte` — custom wallpaper

The simulator retains its upstream MIT license. See
[THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) and
[demo/LICENSE](./demo/LICENSE).

## Ivisyx film

A 2:20 Apple-style product film that drives the live app: the camera pushes in
while a scripted cursor flies the NJ map, drags a deal, and drafts an IC memo.
It includes chapters, captions, a transcript, 16:9 / 1:1 / 9:16 cuts, an
explore mode, and one-click video recording.

```bash
npm run film         # http://localhost:4620
```

See [film/README.md](./film/README.md).

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
