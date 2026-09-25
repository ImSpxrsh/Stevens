"""Build a normalized NJ records file from downloaded public datasets.

    python -m gauge.sources.build --formd-dir data/local/raw/formd \\
        --sbir-csv data/local/raw/sbir/award_data.csv --out data/local/records_nj.json

Downloads (both public, no key needed):

* Form D quarterly zips from
  https://www.sec.gov/data-research/sec-markets-data/form-d-data-sets
  (SEC asks for a User-Agent with a contact email on automated requests)
* SBIR/STTR awards CSV from https://data.www.sbir.gov/awarddatapublic/award_data.csv
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence

from gauge.core.serialize import dump_records
from gauge.sources import formd, sbir


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gauge.sources.build")
    parser.add_argument("--formd-dir")
    parser.add_argument("--sbir-csv")
    parser.add_argument("--state", action="append", default=None)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    states = args.state or ["NJ"]

    records = []
    if args.formd_dir:
        records += formd.read_directory(args.formd_dir, states)
    if args.sbir_csv:
        records += sbir.read_awards(args.sbir_csv, states)
    dump_records(records, args.out)
    counts = Counter(r.provenance.source_type.value for r in records)
    print(f"wrote {len(records)} records to {args.out}: {dict(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
