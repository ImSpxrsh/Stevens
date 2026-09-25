"""Runtime settings, read from environment variables (see .env.example).

Nothing here has a secret default. Values are read at call time so tests
and scripts can override them with environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    """Minimal .env loader: KEY=VALUE lines, existing environment wins."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    db_path: Path
    data_dir: Path
    demo_mode: bool
    sec_user_agent: str | None
    enable_uspto: bool
    cors_origins: tuple[str, ...]

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"


def get_settings() -> Settings:
    _load_dotenv()
    data_dir = Path(os.environ.get("GAUGE_DATA_DIR", REPO_ROOT / "data" / "local"))
    return Settings(
        db_path=Path(os.environ.get("GAUGE_DB_PATH", data_dir / "gauge.sqlite3")),
        data_dir=data_dir,
        demo_mode=os.environ.get("GAUGE_DEMO_MODE", "0") == "1",
        sec_user_agent=os.environ.get("SEC_USER_AGENT") or None,
        enable_uspto=os.environ.get("GAUGE_ENABLE_USPTO", "0") == "1",
        cors_origins=tuple(
            o.strip()
            for o in os.environ.get("GAUGE_CORS_ORIGINS", "http://localhost:5173").split(",")
            if o.strip()
        ),
    )
