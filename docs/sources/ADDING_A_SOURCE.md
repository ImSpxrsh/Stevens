# Adding a source adapter

Every public-record source implements `gauge.sources.base.SourceAdapter`.
The base class runs the lifecycle, records the run in `importer_runs`,
hashes each raw payload into `raw_source_records`, and persists only valid,
new records. Downstream code never sees raw payload shapes.

```python
class MyAdapter(SourceAdapter):
    name = "my-source"                       # shown in job output
    source_type = SourceType.MY_SOURCE       # add to SourceType first
    allowed_domains = ("example.gov",)       # provenance URLs must be on these hosts

    def fetch(self, ctx):                    # download into ctx.raw_dir / "my-source" /
        dest = ctx.raw_dir / "my-source" / "latest.json"
        ctx.http.download(URL, dest)         # conditional GET; SEC hosts need SEC_USER_AGENT
        return [RawPayload("latest.json", URL, dest)]

    def parse(self, payload):                # source-shaped rows
        yield from json.loads(payload.path.read_text())["items"]

    def normalize(self, row, payload, ctx):  # -> NormalizedRecord, None (skip), or raise RecordRejected
        if row["state"] != "NJ":
            return None
        return NormalizedRecord(provenance=Provenance(...), name=row["name"], ...)
```

Rules:

- **Provenance is required.** `Provenance` rejects a missing id or non-HTTP
  URL; `validate` also rejects URLs off `allowed_domains`, future dates, and
  the wrong source type.
- **Bad rows fail loudly, not silently.** Raise `RecordRejected` (or let a
  `ValueError` propagate) from `normalize`: the row is counted, its error is
  reported in the run summary, and it is never persisted. Fetch or parse
  errors fail the whole run and are recorded in `importer_runs.error`.
- **Never read personal data you don't need.** Restrict parsed columns to
  what the record uses (see `gauge/sources/sbir.py`).
- **Be idempotent.** Stable `source_id`s make reruns add nothing
  (`UNIQUE (source_type, source_id)`).

Then register a job in `gauge/sources/jobs.py`:

```python
@job("ingest-my-source", "What it does.", daily=True)
def ingest_my_source() -> str:
    return _run(MyAdapter())
```

and add a test with a fake `Http` (see `tests/sources/test_adapters.py`).

Existing adapters: `FormDDataSetAdapter`, `SbirAwardsAdapter`
(`gauge/sources/adapters.py`), the EDGAR daily-index watch and NJEDA/CSIT
announcement watch (`gauge/sources/watch.py`), and USPTO trademarks
(`gauge/sources/uspto.py`, behind `GAUGE_ENABLE_USPTO`).
