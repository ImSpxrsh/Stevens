# Coverage audit (stretch)

What share of known New Jersey startups does Gauge find, overall and by
sector? Why were the rest missed? (#23)

## 1. Build the reference list

Fill `templates/reference_startups.csv` (`name, town, sector, source`).

- **Use sources independent of Gauge's inputs.** A list built from Form D or
  SBIR/STTR data would inflate coverage. Better sources: accelerator and
  incubator cohort pages, a partner fund's portfolio or pipeline, university
  spinout lists, and press coverage of NJ startups.
- Record the **source for every row**, and keep sector labels coarse and
  consistent (e.g. `life sciences`, `software`, `climate`, `hardware`,
  `fintech`).
- Aim for **at least 30** companies. Below that, or with unsourced rows, the
  report presents coverage as a pilot step instead of a proof number.

## 2. Run it

```bash
python -m gauge.validation.coverage RECORDS.json reference_startups.csv --as-of 2026-09-25 \
    --out data/local/coverage.md --csv data/local/coverage.csv
```

## 3. Read the result

Each reference company gets one outcome:

| Outcome | Meaning | What it suggests |
|---|---|---|
| `found` | In the likely-startup discovery list | |
| `found_uncertain` | Found, held in the uncertain list | Counts as found; review it |
| `excluded` | A hard exclusion rule removed it | Check the rule |
| `classified_not_startup` | Scored not a startup | Classifier false negative |
| `out_of_state` | No linked record has an NJ address | Address data or HQ question |
| `ambiguous` | Several companies share the name | Add the town to the reference row |
| `no_public_signal` | No Form D or SBIR/STTR record | Source blind spot: needs new sources |

If the list is small or coverage is low, present it honestly in the demo as a
pilot step ("we will measure coverage against the fund's own pipeline"),
not as an MVP proof claim.
