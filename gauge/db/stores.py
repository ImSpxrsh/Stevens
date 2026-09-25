"""Database-backed review queue and alert log.

Same interfaces as the JSON-file versions (``gauge.review.store.ReviewStore``
and ``gauge.alerts.AlertLog``), so the linker, alert gate, CLI, and API work
unchanged. Review decisions are append-only rows.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime

from gauge.alerts.feed import Alert, AlertLog, AlertStatus, AlertType
from gauge.core.models import Provenance, SourceType
from gauge.review.models import Action, ActorType, Decision, ReviewItem, ReviewKind
from gauge.review.store import ReviewStore


class SqliteReviewStore(ReviewStore):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        super().__init__(self._load())

    def _load(self) -> list[ReviewItem]:
        reasons: dict[str, list[str]] = {}
        for r in self.conn.execute(
            "SELECT * FROM review_item_reasons ORDER BY review_item_id, position"
        ):
            reasons.setdefault(r["review_item_id"], []).append(r["reason"])
        evidence: dict[str, list[Provenance]] = {}
        for r in self.conn.execute(
            "SELECT * FROM review_item_evidence ORDER BY review_item_id, position"
        ):
            evidence.setdefault(r["review_item_id"], []).append(
                Provenance(
                    SourceType(r["source_type"]),
                    r["source_id"],
                    r["source_url"],
                    date.fromisoformat(r["source_date"]),
                )
            )
        decisions: dict[str, list[Decision]] = {}
        for r in self.conn.execute("SELECT * FROM review_decisions ORDER BY review_item_id, id"):
            decisions.setdefault(r["review_item_id"], []).append(
                Decision(
                    Action(r["action"]),
                    r["actor"],
                    ActorType(r["actor_type"]),
                    datetime.fromisoformat(r["decided_at"]),
                    r["note"],
                    json.loads(r["details_json"]),
                )
            )
        return [
            ReviewItem(
                kind=ReviewKind(r["kind"]),
                subject=r["subject"],
                candidate_company_id=r["candidate_company_id"],
                score=r["score"],
                reasons=tuple(reasons.get(r["id"], ())),
                evidence=tuple(evidence.get(r["id"], ())),
                created_at=datetime.fromisoformat(r["created_at"]),
                decisions=decisions.get(r["id"], []),
            )
            for r in self.conn.execute("SELECT * FROM review_items")
        ]

    def add(self, item: ReviewItem) -> ReviewItem:
        existing = self._items.get(item.item_id)
        if existing is not None:
            return existing
        with self.conn:
            self.conn.execute(
                "INSERT INTO review_items VALUES (?,?,?,?,?,?)",
                (item.item_id, item.kind.value, item.subject, item.candidate_company_id,
                 item.score, item.created_at.isoformat()),
            )  # fmt: skip
            self.conn.executemany(
                "INSERT INTO review_item_reasons VALUES (?,?,?)",
                [(item.item_id, i, reason) for i, reason in enumerate(item.reasons)],
            )
            self.conn.executemany(
                "INSERT INTO review_item_evidence VALUES (?,?,?,?,?,?)",
                [
                    (item.item_id, i, p.source_type.value, p.source_id, p.source_url,
                     p.source_date.isoformat())
                    for i, p in enumerate(item.evidence)
                ],
            )  # fmt: skip
        self._items[item.item_id] = item
        return item

    def decide(self, item_id, action, actor, actor_type=ActorType.HUMAN, note="", details=None):
        item = super().decide(item_id, action, actor, actor_type, note, details)
        d = item.decisions[-1]
        with self.conn:
            self.conn.execute(
                """INSERT INTO review_decisions
                   (review_item_id, action, actor, actor_type, decided_at, note, details_json)
                   VALUES (?,?,?,?,?,?,?)""",
                (item_id, d.action.value, d.actor, d.actor_type.value, d.at.isoformat(), d.note,
                 json.dumps(d.details, sort_keys=True, default=str)),
            )  # fmt: skip
        return item


class SqliteAlertLog(AlertLog):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__(None)
        self.conn = conn
        for r in conn.execute("SELECT * FROM alerts"):
            self._alerts[r["id"]] = Alert(
                alert_id=r["id"],
                type=AlertType(r["type"]),
                company_id=r["company_id"],
                company_name=r["company_name"],
                record_key=r["record_key"],
                summary=r["summary"],
                why=r["why"],
                source_url=r["source_url"],
                source_date=r["source_date"],
                status=AlertStatus(r["status"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )

    def _save(self) -> None:
        with self.conn:
            for a in self._alerts.values():
                self.conn.execute(
                    """INSERT INTO alerts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT (id) DO UPDATE SET status = excluded.status,
                       why = excluded.why, updated_at = excluded.updated_at""",
                    (a.alert_id, a.type.value, a.company_id, a.company_name, a.record_key,
                     a.summary, a.why, a.source_url, a.source_date, a.status.value, a.created_at,
                     a.updated_at),
                )  # fmt: skip

    def get(self, alert_id: str) -> Alert:
        return self._alerts[alert_id]
