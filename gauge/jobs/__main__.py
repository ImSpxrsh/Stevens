"""Run background jobs.

    python -m gauge.jobs list
    python -m gauge.jobs run <job> [<job> ...]
    python -m gauge.jobs daily          # every job in the daily schedule, in order

Jobs register themselves in ``gauge.jobs.registry``. Each returns a short
summary line; a failing job is reported and the rest still run, and the
exit code is nonzero if any job failed.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from gauge.jobs.registry import DAILY, JOBS, load_job_modules, run_jobs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gauge.jobs")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("jobs", nargs="+")
    sub.add_parser("daily")
    args = parser.parse_args(argv)
    load_job_modules()

    if args.command == "list":
        for name, job in JOBS.items():
            flag = " (daily)" if name in DAILY else ""
            print(f"{name}{flag}: {job.description}")
        return 0
    names = DAILY if args.command == "daily" else args.jobs
    unknown = [n for n in names if n not in JOBS]
    if unknown:
        print(f"unknown job(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    results = run_jobs(names)
    for res in results:
        print(f"[{'ok' if res.ok else 'FAILED'}] {res.name}: {res.summary}")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
