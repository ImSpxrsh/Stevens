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


@job("watch-edgar", "Scan the EDGAR daily index for new NJ Form D filings (#13).", daily=True)
def watch_edgar() -> str:
    from gauge.sources.watch import EdgarDailyFormDAdapter

    return _run(EdgarDailyFormDAdapter(lookback_days=5))


@job(
    "watch-announcements",
    "Scan NJEDA and CSIT posts for awards; extract with Claude if enabled (#14).",
    daily=True,
)
def watch_announcements() -> str:
    from datetime import date, timedelta

    from gauge.core.models import SourceType
    from gauge.db.stores import SqliteReviewStore
    from gauge.sources.watch import FEEDS, extract_pending, fetch_posts, llm_enabled, store_posts

    conn, ctx = job_database(), fetch_context()
    since = date.today() - timedelta(days=30)
    enabled = llm_enabled()
    new = relevant = 0
    for source_type in FEEDS:
        posts = fetch_posts(ctx.http, SourceType(source_type), since, ctx.raw_dir)
        pending = store_posts(conn, posts, llm=enabled)
        new += len(posts)
        relevant += len(pending)
    if not enabled:
        return f"{new} posts checked; LLM extraction disabled (set ANTHROPIC_API_KEY to enable)"
    from gauge.ai.claude import ClaudeJsonLLM

    processed, added = extract_pending(conn, ClaudeJsonLLM(), SqliteReviewStore(conn))
    return (
        f"{new} posts checked, {relevant} new relevant; "
        f"{processed} extracted, {added} records added"
    )
