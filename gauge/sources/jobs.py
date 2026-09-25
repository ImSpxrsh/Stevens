"""Daily ingestion jobs for the bulk sources."""

from __future__ import annotations

from gauge.jobs.context import fetch_context, job_database
from gauge.jobs.registry import job
from gauge.sources.adapters import FormDDataSetAdapter, SbirAwardsAdapter
from gauge.sources.base import SourceAdapter


def _run(adapter: SourceAdapter) -> str:
    summary = adapter.run(job_database(), fetch_context())
    if summary.failed:
        raise RuntimeError(summary.line())
    return summary.line()


@job(
    "ingest-formd", "Download new SEC Form D quarterly data sets and import NJ issuers.", daily=True
)
def ingest_formd() -> str:
    return _run(FormDDataSetAdapter())


@job("ingest-sbir", "Refresh the SBIR.gov award download and import NJ awards.", daily=True)
def ingest_sbir() -> str:
    return _run(SbirAwardsAdapter())
