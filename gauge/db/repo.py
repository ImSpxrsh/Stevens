"""Read and write Gauge data in the database.

Source records are upserted (never duplicated: ``UNIQUE (source_type,
source_id)``). Everything derived from them (companies, links, evidence,
program matches) is replaced on each pipeline run, so the tables always
reflect the latest run. Review decisions and alert statuses live in their
own stores (``gauge.db.stores``) and survive reruns.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import UTC, date, datetime
from typing import Any

from gauge.core.models import (
    Address,
    FormDFacts,
    NormalizedRecord,
    Provenance,
    SbirFacts,
    SbirPhase,
    SourceType,
)
from gauge.core.names import normalize_company_name, normalize_town
from gauge.pipeline import PipelineOutput
from gauge.programs.base import Basis


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def _bool(v: bool | None) -> int | None:
    return None if v is None else int(v)


# --- Source records -----------------------------------------------------------


def upsert_records(
    conn: sqlite3.Connection,
    records: Iterable[NormalizedRecord],
    importer_run_id: int | None = None,
) -> tuple[int, int]:
    """Insert new records, skipping ones already stored. Returns (added, skipped)."""
    added = skipped = 0
    with conn:
        for r in records:
            p, a = r.provenance, r.address or Address()
            cur = conn.execute(
                """INSERT OR IGNORE INTO source_records
                   (record_key, source_type, source_id, source_url, source_date, name,
                    name_normalized, cik, street, city, state, postal_code, importer_run_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (r.key, p.source_type.value, p.source_id, p.source_url, p.source_date.isoformat(),
                 r.name, normalize_company_name(r.name), r.cik, a.street, a.city, a.state,
                 a.postal_code, importer_run_id),
            )  # fmt: skip
            if cur.rowcount == 0:
                skipped += 1
                continue
            added += 1
            rid = cur.lastrowid
            if r.form_d:
                f = r.form_d
                conn.execute(
                    """INSERT INTO form_d_facts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (rid, f.industry_group, int(f.is_pooled_investment_fund), f.entity_type,
                     f.jurisdiction_of_incorporation, f.year_of_incorporation,
                     _bool(f.incorporated_within_five_years), f.revenue_range,
                     f.total_offering_amount, f.total_amount_sold, _iso(f.date_of_first_sale),
                     int(f.is_amendment)),
                )  # fmt: skip
                conn.executemany(
                    "INSERT INTO form_d_securities VALUES (?,?,?)",
                    [(rid, i, s) for i, s in enumerate(f.securities_offered)],
                )
            if r.sbir:
                s = r.sbir
                conn.execute(
                    """INSERT INTO sbir_facts VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (rid, s.phase.value, s.program, s.agency, s.award_amount, _iso(s.award_start),
                     _iso(s.award_end), s.topic_title, s.abstract, s.employee_count,
                     s.place_of_performance_state),
                )  # fmt: skip
    return added, skipped


def load_records(conn: sqlite3.Connection) -> list[NormalizedRecord]:
    fd = {row["record_id"]: row for row in conn.execute("SELECT * FROM form_d_facts")}
    secs: dict[int, list[str]] = {}
    for row in conn.execute("SELECT * FROM form_d_securities ORDER BY record_id, position"):
        secs.setdefault(row["record_id"], []).append(row["security"])
    sb = {row["record_id"]: row for row in conn.execute("SELECT * FROM sbir_facts")}

    def d(v: str | None) -> date | None:
        return date.fromisoformat(v) if v else None

    out = []
    for row in conn.execute("SELECT * FROM source_records ORDER BY source_date, record_key"):
        rid = row["id"]
        form_d = sbir = None
        if rid in fd:
            f = fd[rid]
            form_d = FormDFacts(
                industry_group=f["industry_group"],
                is_pooled_investment_fund=bool(f["is_pooled_investment_fund"]),
                entity_type=f["entity_type"],
                jurisdiction_of_incorporation=f["jurisdiction_of_incorporation"],
                year_of_incorporation=f["year_of_incorporation"],
                incorporated_within_five_years=None
                if f["incorporated_within_five_years"] is None
                else bool(f["incorporated_within_five_years"]),
                revenue_range=f["revenue_range"],
                total_offering_amount=f["total_offering_amount"],
                total_amount_sold=f["total_amount_sold"],
                date_of_first_sale=d(f["date_of_first_sale"]),
                is_amendment=bool(f["is_amendment"]),
                securities_offered=tuple(secs.get(rid, ())),
            )
        if rid in sb:
            s = sb[rid]
            sbir = SbirFacts(
                phase=SbirPhase(s["phase"]),
                program=s["program"],
                agency=s["agency"],
                award_amount=s["award_amount"],
                award_start=d(s["award_start"]),
                award_end=d(s["award_end"]),
                topic_title=s["topic_title"],
                abstract=s["abstract"],
                employee_count=s["employee_count"],
                place_of_performance_state=s["place_of_performance_state"],
            )
        has_address = any(row[k] for k in ("street", "city", "state", "postal_code"))
        out.append(
            NormalizedRecord(
                provenance=Provenance(
                    SourceType(row["source_type"]),
                    row["source_id"],
                    row["source_url"],
                    date.fromisoformat(row["source_date"]),
                ),
                name=row["name"],
                address=Address(row["street"], row["city"], row["state"], row["postal_code"])
                if has_address
                else None,
                cik=row["cik"],
                form_d=form_d,
                sbir=sbir,
            )
        )
    return out


# --- Importer runs --------------------------------------------------------------


def start_importer_run(conn: sqlite3.Connection, source_type: str) -> int:
    with conn:
        cur = conn.execute(
            "INSERT INTO importer_runs (source_type, started_at, status) VALUES (?, ?, 'running')",
            (source_type, _now()),
        )
    return int(cur.lastrowid)


def finish_importer_run(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    seen: int,
    added: int,
    rejected: int = 0,
    error: str | None = None,
) -> None:
    with conn:
        conn.execute(
            """UPDATE importer_runs SET finished_at = ?, status = ?, records_seen = ?,
               records_added = ?, records_rejected = ?, error = ? WHERE id = ?""",
            (_now(), "failed" if error else "ok", seen, added, rejected, error, run_id),
        )


# --- Derived outputs --------------------------------------------------------------


def save_pipeline_output(conn: sqlite3.Connection, out: PipelineOutput) -> None:
    """Replace companies and everything derived from them with this run's output."""
    record_ids = {
        row["record_key"]: row["id"]
        for row in conn.execute("SELECT id, record_key FROM source_records")
    }
    stamp = _now()
    with conn:
        conn.execute("DELETE FROM companies")  # cascades to links, features, evidence, programs
        for cid, p in out.profiles.items():
            c = out.classifications[cid]
            latest = p.latest_address()
            addr = latest[0] if latest else Address()
            dates = [r.source_date for r in p.records]
            conn.execute(
                """INSERT INTO companies (id, name, name_normalized, town, state, first_seen,
                   last_seen, startup_label, startup_probability, startup_confidence,
                   exclusion_reason, exclusion_explanation, model_version, as_of, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (cid, p.name, normalize_company_name(p.name), addr.city, addr.state,
                 _iso(min(dates)), _iso(max(dates)), c.label.value, c.probability, c.confidence,
                 c.exclusion.reason.value if c.exclusion else None,
                 c.exclusion.explanation if c.exclusion else None, c.model_version,
                 out.as_of.isoformat(), stamp),
            )  # fmt: skip
            conn.executemany(
                "INSERT INTO classification_features VALUES (?,?,?,?,?)",
                [
                    (cid, i, f.name, f.description, f.contribution)
                    for i, f in enumerate(c.top_features)
                ],
            )
            for r in p.records:
                link = out.linking.links.get(r.key)
                if link is None or r.key not in record_ids:
                    continue
                conn.execute(
                    "INSERT INTO company_source_links VALUES (?,?,?,?,?)",
                    (record_ids[r.key], cid, link.basis.value, link.review_item_id, stamp),
                )
            conn.executemany(
                """INSERT INTO evidence_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    (cid, i, e.kind.value, e.claim, e.value, e.confidence, e.limitations,
                     e.extracted_by, e.source.source_type.value if e.source else None,
                     e.source.source_id if e.source else None,
                     e.source.source_url if e.source else None,
                     _iso(e.source.source_date) if e.source else None)
                    for i, e in enumerate(out.evidence_cards.get(cid, []))
                ],
            )  # fmt: skip
            for pid, m in out.program_matches.get(cid, {}).items():
                conn.execute(
                    "INSERT INTO program_matches VALUES (?,?,?,?,?,?,?)",
                    (cid, pid, m.program_name, m.result.value, m.summary, m.rules_version,
                     m.as_of.isoformat()),
                )  # fmt: skip
                position = 0
                for chk in m.checks:
                    conn.execute(
                        "INSERT INTO program_match_checks VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (cid, pid, position, chk.criterion.id, chk.criterion.text,
                         Basis.SCREENED.value, chk.outcome.value, chk.explanation,
                         int(chk.needs_confirmation), chk.criterion.verification_question,
                         chk.criterion.source.url),
                    )  # fmt: skip
                    conn.executemany(
                        "INSERT OR IGNORE INTO program_match_check_evidence VALUES (?,?,?,?)",
                        [
                            (cid, pid, position, f"{e.source_type}:{e.source_id}")
                            for e in chk.evidence
                        ],
                    )
                    position += 1
                for crit in m.confirm_before_applying:
                    conn.execute(
                        "INSERT INTO program_match_checks VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (cid, pid, position, crit.id, crit.text, Basis.ATTESTED.value, None, None,
                         0, crit.verification_question, crit.source.url),
                    )  # fmt: skip
                    position += 1


# --- Reads for the API and UI --------------------------------------------------------


def _rows(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(r) for r in cur.fetchall()]


def list_companies(
    conn: sqlite3.Connection,
    *,
    query: str = "",
    town: str | None = None,
    county: str | None = None,
    sector: str | None = None,
    label: str | None = None,
    include_excluded: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    where, args = [], []
    if query:
        where.append(
            "(c.name_normalized LIKE ? OR c.id = ? OR c.id IN "
            "(SELECT l.company_id FROM company_source_links l JOIN source_records s ON s.id = l.record_id "
            " WHERE s.source_id = ? OR s.cik = ?))"
        )
        args += [f"%{normalize_company_name(query)}%", query, query, query]
    if town:
        where.append("lower(c.town) = ?")
        args.append(normalize_town(town))
    if county:
        where.append("c.county = ?")
        args.append(county)
    if sector:
        where.append("c.sector = ?")
        args.append(sector)
    if label:
        where.append("c.startup_label = ?")
        args.append(label)
    if not include_excluded:
        where.append("c.exclusion_reason IS NULL")
    sql = "SELECT c.*, (SELECT count(*) FROM company_source_links l WHERE l.company_id = c.id) AS record_count FROM companies c"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY c.startup_probability DESC NULLS LAST, c.name LIMIT ? OFFSET ?"
    return _rows(conn.execute(sql, [*args, limit, offset]))


def get_company(conn: sqlite3.Connection, company_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    if row is None:
        return None
    company = dict(row)
    company["records"] = _rows(
        conn.execute(
            """SELECT s.record_key, s.source_type, s.source_id, s.source_url, s.source_date, s.name,
                      s.city, s.state, s.postal_code, l.basis, l.review_item_id
               FROM company_source_links l JOIN source_records s ON s.id = l.record_id
               WHERE l.company_id = ? ORDER BY s.source_date""",
            (company_id,),
        )
    )
    company["features"] = _rows(
        conn.execute(
            "SELECT feature, description, contribution FROM classification_features "
            "WHERE company_id = ? ORDER BY position",
            (company_id,),
        )
    )
    company["evidence"] = _rows(
        conn.execute(
            "SELECT * FROM evidence_items WHERE company_id = ? ORDER BY position", (company_id,)
        )
    )
    programs = _rows(
        conn.execute(
            "SELECT * FROM program_matches WHERE company_id = ? ORDER BY program_id", (company_id,)
        )
    )
    for p in programs:
        checks = _rows(
            conn.execute(
                "SELECT * FROM program_match_checks WHERE company_id = ? AND program_id = ? ORDER BY position",
                (company_id, p["program_id"]),
            )
        )
        for chk in checks:
            chk["evidence"] = [
                r["record_key"]
                for r in conn.execute(
                    "SELECT record_key FROM program_match_check_evidence "
                    "WHERE company_id = ? AND program_id = ? AND position = ?",
                    (company_id, p["program_id"], chk["position"]),
                )
            ]
        p["checks"] = checks
    company["programs"] = programs
    return company


def map_points(conn: sqlite3.Connection, *, include_excluded: bool = False) -> list[dict[str, Any]]:
    sql = """SELECT id, name, town, county, sector, latitude, longitude, startup_label,
                    startup_probability, first_seen, last_seen FROM companies
             WHERE latitude IS NOT NULL"""
    if not include_excluded:
        sql += " AND exclusion_reason IS NULL"
    return _rows(conn.execute(sql))


def summary(conn: sqlite3.Connection) -> dict[str, Any]:
    def one(sql: str) -> int:
        return int(conn.execute(sql).fetchone()[0])

    return {
        "records": one("SELECT count(*) FROM source_records"),
        "companies": one("SELECT count(*) FROM companies"),
        "likely_startups": one("SELECT count(*) FROM companies WHERE startup_label = 'likely_startup' AND exclusion_reason IS NULL"),
        "uncertain": one("SELECT count(*) FROM companies WHERE startup_label = 'uncertain' AND exclusion_reason IS NULL"),
        "excluded": one("SELECT count(*) FROM companies WHERE exclusion_reason IS NOT NULL"),
        "open_reviews": one(
            "SELECT count(*) FROM review_items r WHERE NOT EXISTS (SELECT 1 FROM review_decisions d "
            "WHERE d.review_item_id = r.id AND d.action <> 'annotate')"
        ),
        "alerts_ready": one("SELECT count(*) FROM alerts WHERE status = 'ready'"),
        "alerts_held": one("SELECT count(*) FROM alerts WHERE status = 'held'"),
        "as_of": (conn.execute("SELECT max(as_of) FROM companies").fetchone()[0]),
    }  # fmt: skip
