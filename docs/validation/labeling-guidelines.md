# Labeling guidelines: is this company a startup?

Used for the 100-record classifier precision check (#22). The goal is a
number we can defend on the proof slide, so consistency matters more than
speed.

## Before you start

- Label **blind**. The sheet deliberately omits Gauge's label and score; do
  not look them up in the app while labeling.
- Spend **up to 10 minutes** per row. Use the linked public records, the
  company's website, LinkedIn, and news. Note which source settled it.
- Two people should label the **first 20 rows independently**, compare, and
  settle disagreements before splitting the rest. Record the calibration
  disagreements in the notes column.

## Labels

**`likely_startup`**: all of:
- an independent, privately held operating company (not a subsidiary or a
  holding/financing vehicle);
- building a product or technology meant to scale (software, hardware, life
  sciences, climate, deep tech, or a tech-enabled service);
- early stage: roughly ten years old or younger, and not yet a large,
  established business.

**`not_startup`**: any of:
- a fund, SPV, investment partnership, or real-estate vehicle;
- a public company or a subsidiary of one;
- an established business: long operating history, large headcount or
  revenue, or a traditional local service or retail business (restaurant,
  contractor, practice, franchise);
- a shell, holding company, or entity with no operating business;
- a nonprofit or university lab (unless spun out as its own company).

**`uncertain`**: the public information cannot settle it in 10 minutes (no
website, conflicting records, a name shared by several businesses). Say why
in the notes. Uncertain rows are reported separately and do not count for
or against precision.

## Notes column

Write a short reason for every `not_startup` and `uncertain` label, e.g.
"Subsidiary of a public medtech company", "Family real-estate LLC", "Two
unrelated companies share this name". The false-positive list in the report
is built from these notes and feeds classifier fixes.

## Scoring

```bash
python -m gauge.validation.precision score data/local/precision/manifest.json \
    data/local/precision/labeling_sheet.csv --out data/local/precision/report.md
```

The report refuses to present a quotable number while rows are unlabeled.
