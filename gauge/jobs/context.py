"""Shared setup for jobs: settings, database, and fetch context."""

from __future__ import annotations

import sqlite3

from gauge.config import get_settings
from gauge.db.connection import open_database
from gauge.sources.base import FetchContext
from gauge.sources.http import Http


def job_database() -> sqlite3.Connection:
    return open_database(get_settings().db_path)


def fetch_context() -> FetchContext:
    s = get_settings()
    return FetchContext(raw_dir=s.raw_dir, http=Http(user_agent=s.sec_user_agent))
