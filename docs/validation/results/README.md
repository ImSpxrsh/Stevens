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
