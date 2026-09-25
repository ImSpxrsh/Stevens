# Gauge

Gauge finds early-stage New Jersey startups in public records (SEC Form D,
SBIR/STTR awards, NJEDA/CSIT announcements), explains why each one surfaced,
and checks it against New Jersey funding programs.

## Status

This is a minimal Python core. It holds only the shared domain types that the
classifier, program-rule, review, and validation work builds on:

- `gauge/core/models.py`: normalized source records with required provenance,
  canonical company profiles, and evidence items that keep facts, inferred
  labels, and unknowns apart.
- `gauge/core/names.py`: company-name and town normalization.

The full application scaffold (web app, jobs, database) is tracked in
[#27](https://github.com/ImSpxrsh/Stevens/issues/27), the architecture in
[#1](https://github.com/ImSpxrsh/Stevens/issues/1), and the schema in
[#28](https://github.com/ImSpxrsh/Stevens/issues/28). Those can extend or
replace these types.

## Setup

Requires Python 3.12+.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

For the LLM-assisted features, install the `ai` extra and copy `.env.example`
to `.env`:

```bash
pip install -e ".[dev,ai]"
```

## Commands

```bash
pytest              # run tests
ruff check .        # lint
ruff format .       # format
```
