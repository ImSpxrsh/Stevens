"""SQLite connections and the migration runner."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

MIGRATIONS = Path(__file__).parent / "migrations"


def connect(path: str | Path) -> sqlite3.Connection:
    """Open the database with foreign keys on and rows addressable by column name."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL") if str(path) != ":memory:" else None
    return conn


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply every migration not yet recorded, in filename order. Returns what ran."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    applied = []
    for path in sorted(MIGRATIONS.glob("*.sql")):
        version = path.stem
        if version in done:
            continue
        with conn:
            conn.executescript(path.read_text())
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, datetime.now(UTC).isoformat()),
            )
        applied.append(version)
    return applied


def open_database(path: str | Path) -> sqlite3.Connection:
    conn = connect(path)
    migrate(conn)
    return conn
