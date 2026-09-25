"""Jobs that run after ingestion. Loaded last so they run last in the daily schedule."""

from __future__ import annotations

from datetime import date

from gauge.db.refresh import refresh
from gauge.jobs.context import job_database
from gauge.jobs.registry import job


@job("refresh", "Relink, reclassify, rematch programs, and add new alerts.", daily=True)
def refresh_all() -> str:
    result = refresh(job_database(), date.today())
    return (
        f"{result.companies} companies, {result.new_alerts} new alerts, "
        f"{result.open_reviews} open reviews"
    )
