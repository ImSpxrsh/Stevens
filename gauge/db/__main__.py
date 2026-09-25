"""Database commands.

    python -m gauge.db init                       # create or migrate the database
    python -m gauge.db seed --fixtures            # load the golden fixtures (frontend work, demos)
    python -m gauge.db seed --records data/local/records_nj.json --as-of 2026-06-30
    python -m gauge.db status

The database path comes from GAUGE_DB_PATH (default data/local/gauge.sqlite3).
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date

from gauge.config import get_settings
from gauge.core.serialize import load_records
from gauge.db.connection import migrate, open_database
from gauge.db.refresh import refresh
from gauge.db.repo import finish_importer_run, start_importer_run, summary, upsert_records


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gauge.db")
    parser.add_argument("--db", help="database path (default: GAUGE_DB_PATH)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    seed = sub.add_parser("seed")
    src = seed.add_mutually_exclusive_group(required=True)
    src.add_argument("--fixtures", action="store_true")
    src.add_argument("--records")
    seed.add_argument("--as-of", type=date.fromisoformat)
    sub.add_parser("status")
    args = parser.parse_args(argv)

    conn = open_database(args.db or get_settings().db_path)
    if args.command == "init":
        print(f"migrations applied: {migrate(conn) or 'none (up to date)'}")
        return 0
    if args.command == "seed":
        from gauge.golden import AS_OF, RECORDS

        path = RECORDS if args.fixtures else args.records
        as_of = args.as_of or (AS_OF if args.fixtures else date.today())
        run_id = start_importer_run(conn, "fixtures" if args.fixtures else "records_file")
        records = load_records(path)
        added, _ = upsert_records(conn, records, run_id)
        finish_importer_run(conn, run_id, seen=len(records), added=added)
        result = refresh(conn, as_of)
        print(
            f"added {added} of {len(records)} records; {result.companies} companies, "
            f"{result.new_alerts} new alerts, {result.open_reviews} open reviews (as of {as_of})"
        )
        return 0
    for key, value in summary(conn).items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
