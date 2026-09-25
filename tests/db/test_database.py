import sqlite3
from datetime import date

import pytest

from gauge.alerts import AlertStatus
from gauge.core.serialize import load_records as load_json
from gauge.db.__main__ import main as db_main
from gauge.db.connection import connect, migrate, open_database
from gauge.db.refresh import refresh
from gauge.db.repo import (
    get_company,
    list_companies,
    load_records,
    map_points,
    summary,
    upsert_records,
)
from gauge.db.stores import SqliteAlertLog, SqliteReviewStore
from gauge.golden import AS_OF, RECORDS
from gauge.review import Action


@pytest.fixture
def db(tmp_path):
    conn = open_database(tmp_path / "g.sqlite3")
    upsert_records(conn, load_json(RECORDS))
    refresh(conn, AS_OF)
    return conn


def test_migrations_create_a_clean_database_and_are_idempotent(tmp_path):
    conn = connect(tmp_path / "x.sqlite3")
    assert migrate(conn) == ["0001_initial"]
    assert migrate(conn) == []
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for t in ("importer_runs", "raw_source_records", "source_records", "companies",
              "company_source_links", "evidence_items", "program_matches", "alerts",
              "review_items", "review_decisions", "validation_runs"):  # fmt: skip
        assert t in tables


def test_records_round_trip_and_source_ids_are_unique(tmp_path):
    conn = open_database(tmp_path / "x.sqlite3")
    records = load_json(RECORDS)
    assert upsert_records(conn, records) == (len(records), 0)
    assert upsert_records(conn, records) == (0, len(records))
    assert load_records(conn) == sorted(records, key=lambda r: (r.source_date, r.key))


def test_company_detail_has_records_evidence_and_program_checks(db):
    c = get_company(db, "cik:0009000003")
    assert c["name"] == "Northbeam Analytics, Inc." and c["startup_label"] == "likely_startup"
    assert {r["basis"] for r in c["records"]} == {"exact_cik", "exact_name_postal"}
    assert {e["kind"] for e in c["evidence"]} == {"fact", "inferred", "unknown"}
    assert all(e["source_url"] for e in c["evidence"] if e["kind"] == "fact")
    angel = next(p for p in c["programs"] if p["program_id"] == "nj_angel_investor_tax_credit")
    assert angel["result"] == "strong_match"
    screened = [chk for chk in angel["checks"] if chk["basis"] == "screened"]
    assert all(chk["evidence"] for chk in screened)
    assert any(chk["basis"] == "attested" for chk in angel["checks"])


def test_list_filters(db):
    likely = list_companies(db, label="likely_startup")
    assert likely and all(c["startup_label"] == "likely_startup" for c in likely)
    assert [c["id"] for c in list_companies(db, query="halyard")] == ["cik:0009000001"]
    assert [c["id"] for c in list_companies(db, query="0009000003")] == ["cik:0009000003"]
    assert [c["name"] for c in list_companies(db, town="Princeton")] == [
        "Pinewood Therapeutics LLC"
    ]
    assert all(c["exclusion_reason"] is None for c in list_companies(db))
    assert any(c["exclusion_reason"] for c in list_companies(db, include_excluded=True))
    assert summary(db)["excluded"] == 1


def test_fact_evidence_without_source_is_rejected(db):
    with pytest.raises(sqlite3.IntegrityError):
        with db:
            db.execute("INSERT INTO evidence_items (company_id, position, kind, claim) "
                       "VALUES ('cik:0009000001', 999, 'fact', 'unsourced')")  # fmt: skip


def test_review_decisions_persist_and_drive_the_next_refresh(db, tmp_path):
    store = SqliteReviewStore(db)
    (item,) = store.items()
    store.decide(item.item_id, Action.APPROVE_MERGE, "Priya", note="same founders")
    reloaded = SqliteReviewStore(db).get(item.item_id)
    assert reloaded.decisions[-1].actor == "Priya" and reloaded.status.value == "approved"
    refresh(db, AS_OF)
    merged = get_company(db, "cik:0009000005")
    assert {r["basis"] for r in merged["records"]} == {"exact_cik", "human_approved"}
    for sql in (
        "UPDATE review_decisions SET actor = 'someone else'",
        "DELETE FROM review_decisions",
    ):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            with db:
                db.execute(sql)


def test_alerts_dedupe_and_keep_status(db):
    first = SqliteAlertLog(db).alerts()
    assert first
    SqliteAlertLog(db).set_status(first[0].alert_id, AlertStatus.DISMISSED)
    assert refresh(db, AS_OF).new_alerts == 0
    assert SqliteAlertLog(db).get(first[0].alert_id).status is AlertStatus.DISMISSED
    assert db.execute("SELECT count(*) FROM alerts").fetchone()[0] == len(first)


def test_map_points_need_coordinates(db):
    assert map_points(db) == []  # geocoding (#5) fills latitude/longitude


def test_cli_seed_and_status(tmp_path, capsys):
    path = str(tmp_path / "cli.sqlite3")
    assert db_main(["--db", path, "seed", "--fixtures"]) == 0
    assert "added 9 of 9 records" in capsys.readouterr().out
    assert db_main(["--db", path, "status"]) == 0
    assert "companies: 7" in capsys.readouterr().out
    assert date.fromisoformat(summary(open_database(path))["as_of"]) == AS_OF
