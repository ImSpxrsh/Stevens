"""The contract every public-record source implements.

Lifecycle, run by ``SourceAdapter.run``:

1. ``fetch``: download raw payloads into ``data/local/raw/<source>/``.
2. ``parse``: turn a payload into source-shaped rows (dicts).
3. ``normalize``: turn one row into a ``NormalizedRecord`` (or ``None`` to
   skip it, e.g. an out-of-state issuer). Raise ``RecordRejected`` for a row
   that is malformed.
4. ``validate``: shared checks every record must pass (provenance from the
   right domain, no future dates, known source type).
5. persist: new records are inserted; ones already stored are skipped.

A bad row is counted and reported, never persisted, and never stops the run;
an error in fetch or parse fails the run and is recorded in
``importer_runs``. Downstream code only ever sees ``NormalizedRecord``s.
See docs/sources/ADDING_A_SOURCE.md.
"""

from __future__ import annotations

import hashlib
import sqlite3
from abc import ABC, abstractmethod
from collections.abc import Collection, Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from gauge.core.models import NormalizedRecord, SourceType
from gauge.db.repo import finish_importer_run, start_importer_run, upsert_records
from gauge.sources.http import Http

MAX_REPORTED_ERRORS = 20


class RecordRejected(ValueError):
    """A row that cannot become a valid record."""


@dataclass(frozen=True)
class RawPayload:
    source_id: str  # stable id for the payload (file name, accession number, post id)
    source_url: str
    path: Path

    def sha256(self) -> str:
        h = hashlib.sha256()
        with open(self.path, "rb") as f:
            while chunk := f.read(1 << 20):
                h.update(chunk)
        return h.hexdigest()


@dataclass
class FetchContext:
    raw_dir: Path
    http: Http
    states: Collection[str] = ("NJ",)
    today: date = field(default_factory=date.today)


@dataclass
class RunSummary:
    source: str
    payloads: int = 0
    seen: int = 0
    added: int = 0
    skipped: int = 0
    filtered: int = 0
    rejected: int = 0
    errors: list[str] = field(default_factory=list)
    failed: str | None = None

    def line(self) -> str:
        if self.failed:
            return f"{self.source}: FAILED ({self.failed})"
        return (
            f"{self.source}: {self.payloads} payloads, {self.seen} rows, {self.added} new, "
            f"{self.skipped} already stored, {self.filtered} filtered, {self.rejected} rejected"
        )


class SourceAdapter(ABC):
    name: str
    source_type: SourceType
    allowed_domains: tuple[str, ...]

    @abstractmethod
    def fetch(self, ctx: FetchContext) -> list[RawPayload]: ...

    @abstractmethod
    def parse(self, payload: RawPayload) -> Iterator[dict[str, Any]]: ...

    @abstractmethod
    def normalize(
        self, row: dict[str, Any], payload: RawPayload, ctx: FetchContext
    ) -> NormalizedRecord | None: ...

    def validate(self, record: NormalizedRecord, ctx: FetchContext) -> None:
        p = record.provenance
        if p.source_type is not self.source_type:
            raise RecordRejected(f"{record.key}: expected {self.source_type}, got {p.source_type}")
        host = urlparse(p.source_url).netloc
        if not any(host == d or host.endswith("." + d) for d in self.allowed_domains):
            raise RecordRejected(
                f"{record.key}: source URL host {host!r} is not an expected source"
            )
        if p.source_date > ctx.today:
            raise RecordRejected(f"{record.key}: source date {p.source_date} is in the future")

    def records(self, payloads: list[RawPayload], ctx: FetchContext, summary: RunSummary):
        for payload in payloads:
            for row in self.parse(payload):
                summary.seen += 1
                try:
                    record = self.normalize(row, payload, ctx)
                    if record is None:
                        summary.filtered += 1
                        continue
                    self.validate(record, ctx)
                except (RecordRejected, ValueError) as e:
                    summary.rejected += 1
                    if len(summary.errors) < MAX_REPORTED_ERRORS:
                        summary.errors.append(f"{payload.source_id}: {e}")
                    continue
                yield record

    def run(self, conn: sqlite3.Connection, ctx: FetchContext) -> RunSummary:
        summary = RunSummary(self.name)
        run_id = start_importer_run(conn, self.source_type.value)
        try:
            payloads = self.fetch(ctx)
            summary.payloads = len(payloads)
            self._record_payloads(conn, payloads, run_id)
            records = list(self.records(payloads, ctx, summary))
            summary.added, summary.skipped = upsert_records(conn, records, run_id)
        except Exception as e:  # fetch/parse failures fail the run, visibly
            summary.failed = f"{type(e).__name__}: {e}"
        finish_importer_run(
            conn,
            run_id,
            seen=summary.seen,
            added=summary.added,
            rejected=summary.rejected,
            error=summary.failed,
        )
        return summary

    def _record_payloads(
        self, conn: sqlite3.Connection, payloads: list[RawPayload], run_id: int
    ) -> None:
        stamp = datetime.now(UTC).isoformat()
        with conn:
            for p in payloads:
                conn.execute(
                    """INSERT INTO raw_source_records
                       (source_type, source_id, source_url, fetched_at, content_sha256,
                        storage_path, importer_run_id)
                       VALUES (?,?,?,?,?,?,?)
                       ON CONFLICT (source_type, source_id) DO UPDATE SET
                         fetched_at = excluded.fetched_at, content_sha256 = excluded.content_sha256,
                         importer_run_id = excluded.importer_run_id""",
                    (
                        self.source_type.value,
                        p.source_id,
                        p.source_url,
                        stamp,
                        p.sha256(),
                        str(p.path),
                        run_id,
                    ),
                )
