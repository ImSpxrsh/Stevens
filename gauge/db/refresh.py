"""Recompute everything derived from the stored records.

Used by the seed command and the daily job: load records, run the pipeline
with the database-backed review queue, replace derived tables, and add new
alerts (deduplicated, statuses preserved).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date, timedelta

from gauge.alerts import generate
from gauge.db.repo import load_records, save_pipeline_output
from gauge.db.stores import SqliteAlertLog, SqliteReviewStore
from gauge.pipeline import PipelineOutput, run

ALERT_LOOKBACK = timedelta(days=90)


@dataclass(frozen=True)
class RefreshResult:
    companies: int
    new_alerts: int
    open_reviews: int
    output: PipelineOutput


def refresh(
    conn: sqlite3.Connection,
    as_of: date,
    *,
    alerts_since: date | None = None,
    public_ciks: Collection[str] = (),
) -> RefreshResult:
    store = SqliteReviewStore(conn)
    out = run(load_records(conn), as_of, store, public_ciks=public_ciks)
    save_pipeline_output(conn, out)
    log = SqliteAlertLog(conn)
    added = log.add(generate(out, store, since=alerts_since or as_of - ALERT_LOOKBACK))
    open_reviews = sum(1 for i in store.items() if i.status.value == "open")
    return RefreshResult(len(out.profiles), len(added), open_reviews, out)
