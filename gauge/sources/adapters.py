"""Bulk adapters for SEC Form D data sets (#2) and SBIR.gov awards (#3)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from gauge.core.models import NormalizedRecord, SourceType
from gauge.sources import formd, sbir
from gauge.sources.base import FetchContext, RawPayload, RecordRejected, SourceAdapter

FORM_D_ZIP = re.compile(r'href="(/files/[^"]*form-d-data-sets/(\d{4}q[1-4])_d\.zip)"')


class FormDDataSetAdapter(SourceAdapter):
    """Quarterly SEC Form D data sets: every Form D, one zip per quarter.

    Published quarters do not change, so only quarters not yet on disk are
    downloaded (plus the newest one, which SEC may republish). New filings
    between releases come from the EDGAR daily-index watch (#13).
    """

    name = "sec-form-d-datasets"
    source_type = SourceType.SEC_FORM_D
    allowed_domains = ("sec.gov",)

    def __init__(self, first_quarter: str = "2019q1") -> None:
        self.first_quarter = first_quarter

    def fetch(self, ctx: FetchContext) -> list[RawPayload]:
        page = ctx.http.get(formd.DATASET_PAGE).decode("utf-8", "replace")
        quarters = sorted(
            {(q, path) for path, q in FORM_D_ZIP.findall(page) if q >= self.first_quarter}
        )
        out_dir = ctx.raw_dir / "formd"
        payloads = []
        for i, (quarter, path) in enumerate(quarters):
            dest = out_dir / f"{quarter}_d.zip"
            newest = i == len(quarters) - 1
            url = f"https://www.sec.gov{path}"
            if not dest.exists() or newest:
                ctx.http.download(url, dest, only_if_newer=True)
            payloads.append(RawPayload(quarter, url, dest))
        return payloads

    def parse(self, payload: RawPayload) -> Iterator[dict[str, Any]]:
        yield from formd.quarter_rows(payload.path)

    def normalize(
        self, row: dict[str, Any], payload: RawPayload, ctx: FetchContext
    ) -> NormalizedRecord | None:
        if formd.issuer_state(row) not in {s.upper() for s in ctx.states}:
            return None
        if not (row["issuer"].get("ENTITYNAME") or "").strip():
            raise RecordRejected(f"{row['accession']}: issuer has no name")
        return formd.row_to_record(row)


class SbirAwardsAdapter(SourceAdapter):
    """SBIR.gov award download. Re-fetched only when the server reports a newer file."""

    name = "sbir-awards"
    source_type = SourceType.SBIR_STTR
    allowed_domains = ("sbir.gov",)

    def fetch(self, ctx: FetchContext) -> list[RawPayload]:
        dest = ctx.raw_dir / "sbir" / "award_data.csv"
        ctx.http.download(sbir.DATASET_URL, dest, only_if_newer=True)
        return [RawPayload("award_data.csv", sbir.DATASET_URL, dest)]

    def parse(self, payload: RawPayload) -> Iterator[dict[str, Any]]:
        yield from sbir.award_rows(payload.path)

    def normalize(
        self, row: dict[str, Any], payload: RawPayload, ctx: FetchContext
    ) -> NormalizedRecord | None:
        if sbir.row_state(row) not in {s.upper() for s in ctx.states}:
            return None
        record = sbir.row_to_record(row)
        if record is None:
            raise RecordRejected(
                f"award for {row.get('Company')!r} has no phase, name, or award date"
            )
        return record


def local_payloads(directory: Path, pattern: str, url: str) -> list[RawPayload]:
    """Payloads for files already on disk (used by tests and offline rebuilds)."""
    return [RawPayload(p.name, url, p) for p in sorted(directory.glob(pattern))]
