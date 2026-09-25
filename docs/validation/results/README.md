# Validation results on real New Jersey data

Data: every NJ-issuer SEC Form D filing in the SEC Form D data sets for
2019 Q1–2026 Q2 (5,948 filings), and every NJ SBIR/STTR award in the
SBIR.gov award download (5,166 awards). Built with `python -m gauge.sources.build`.
The raw files are not committed; see `gauge/sources/build.py` to rebuild.

**Known data gap:** the SBIR.gov bulk file effectively ends in 2023 (23
awards nationwide dated 2024), so SBIR/STTR Phase II outcomes in 2024 are
missing from the backtest.

## #21 Top-25 backtest (frozen 2022-12-31, outcomes through 2024-12-31)

Full report: [backtest-2022.md](backtest-2022.md)

| | Gauge | strongest baseline |
|---|---:|---:|
| All candidates (n=520, base rate 18%) | **3/25** | 7/25 (most recent public record) |
| Cold start (n=168, base rate 18%) | **5/25** | 4/25 (SBIR/STTR award count) |

All 95% intervals overlap, so none of these differences is conclusive.
**What the proof slide can honestly say:** on 2022 data, Gauge's current
ranking did not beat simple baselines at surfacing companies that raised
again or won Phase II within two years; on first-time filers it was level
with them.

Why: the classifier estimates *how startup-like* a company is, not *whether
it will raise again*, and it saturates. 76 candidates tie at Gauge's 25th
score, so the tail of the top 25 is effectively arbitrary. A follow-on ranking
signal is needed; it should be designed on a different period (e.g. a
2021 cutoff) and only then evaluated on this 2022 snapshot, so this result
stays a clean test.

## #22 Precision labeling sample (as of 2026-06-30)

`precision-2026-06-30/labeling_sheet.csv` is the blind sheet for 100
randomly sampled likely-startup companies (seed 2026, from 1,185);
`manifest.json` keeps the predictions for scoring. Label it following
[../labeling-guidelines.md](../labeling-guidelines.md), then:

```bash
python -m gauge.validation.precision score \
    docs/validation/results/precision-2026-06-30/manifest.json \
    docs/validation/results/precision-2026-06-30/labeling_sheet.csv
```

Expect a low number on this first pass. Looking at the population (not the
labels):

- **402 of the 1,185 likely startups first appear in public records before
  2016**, mostly long-running SBIR contractors. The model has no feature for
  age from the first public record, so many awards read as startup signal.
- 41 have a latest Form D in Retailing or Restaurants (e.g. a restaurant
  chain's management entity) and nothing excludes them.
- Public companies are only excluded when a list of public-company SEC IDs
  is passed in, and the pipeline does not load one yet; SBIR-only public
  companies (no SEC ID in the record) cannot be caught that way at all.

These are the classifier fixes to make *after* this sample is labeled, then
re-measure on a fresh sample.

## #23 Coverage audit (as of 2026-06-30)

Reference list: [coverage/reference_startups.csv](coverage/reference_startups.csv),
50 New Jersey startups, each with its source: the 40 honorees of NJBIZ's
*In the Lead 2025: Startups*, and 10 companies NJEDA announced as NJ
Innovation Evergreen Fund investments. Neither source is derived from Form D
or SBIR data. Full report: [coverage/coverage-2026-06-30.md](coverage/coverage-2026-06-30.md).

| | |
|---|---|
| **Found (discovery or uncertain list)** | **15/50 = 30%** (95% CI 19%–44%) |
| Found as likely startup | 11/50 = 22% |
| No Form D or SBIR/STTR record in NJ data | 34/50 |
| Ambiguous (two same-name SBIR companies) | 1 |

- **The main gap is sources, not the classifier.** Of the 34 with no NJ record, a
  nationwide name search found only 4 filing anywhere else, and 2 of those look
  like unrelated companies with the same name. Most of these startups
  (pre-seed, SAFE-funded, grant-funded outside SBIR) never file Form D, so
  Form D + SBIR alone see about a third of recognized NJ startups.
- Two misses are legal-name mismatches the audit now flags for a manual check
  (e.g. *Balcony* files as *Balcony Technology Group, Inc.*); space-insensitive
  names (*JOGO Health* = *JogoHealth, Inc.*) now match automatically.
- Bias: an awards list over-represents very young companies, which makes coverage
  look lower than it would against a list of venture-backed companies. The
  list was compiled by Claude from the cited pages; spot-check it before quoting.
