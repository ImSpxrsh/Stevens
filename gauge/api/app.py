"""Gauge HTTP API.

    uvicorn gauge.api.app:app --reload          # or: make api

Routes are added per area in ``gauge/api/routes_*.py`` (#29). The health
route reports the database and data-source state so ops checks (#25) can
call one URL.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gauge import __version__
from gauge.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Gauge API", version=__version__)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "version": __version__,
            "time": datetime.now(UTC).isoformat(),
            "demo_mode": settings.demo_mode,
        }

    return app


app = create_app()
