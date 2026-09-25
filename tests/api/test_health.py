from fastapi.testclient import TestClient

from gauge import __version__
from gauge.api.app import create_app
from gauge.config import get_settings
from gauge.jobs.__main__ import main as jobs_main


def test_health_route():
    client = TestClient(create_app(get_settings()))
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["version"] == __version__


def test_settings_come_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("GAUGE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GAUGE_DEMO_MODE", "1")
    monkeypatch.delenv("GAUGE_DB_PATH", raising=False)
    s = get_settings()
    assert s.db_path == tmp_path / "gauge.sqlite3" and s.demo_mode


def test_job_runner(capsys):
    assert jobs_main(["run", "noop"]) == 0
    assert "[ok] noop" in capsys.readouterr().out
    assert jobs_main(["run", "missing"]) == 2
