"""Review-item storage.

``JsonReviewStore`` keeps the queue in one JSON file so the team can review
matches during development and demo prep without a database. The schema work
in #28 can swap in a database table behind the same methods.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from gauge.core.models import Provenance, SourceType
from gauge.review.models import (
    Action,
    ActorType,
    Decision,
    ReviewItem,
    ReviewKind,
    ReviewStatus,
    now,
    review_item_id,
)


class UnknownReviewItem(KeyError):
    pass


class ReviewStore:
    """In-memory store; subclasses decide how to persist."""

    def __init__(self, items: Iterable[ReviewItem] = ()) -> None:
        self._items: dict[str, ReviewItem] = {i.item_id: i for i in items}

    def _persist(self) -> None:  # overridden by durable stores
        pass

    def get(self, item_id: str) -> ReviewItem:
        try:
            return self._items[item_id]
        except KeyError:
            raise UnknownReviewItem(item_id) from None

    def find(self, kind: ReviewKind, subject: str, candidate: str) -> ReviewItem | None:
        return self._items.get(review_item_id(kind, subject, candidate))

    def items(self, status: ReviewStatus | None = None) -> list[ReviewItem]:
        found = [i for i in self._items.values() if status is None or i.status is status]
        return sorted(found, key=lambda i: (i.created_at, i.item_id))

    def add(self, item: ReviewItem) -> ReviewItem:
        """Add an item unless one with the same id exists; the existing one keeps its history."""
        existing = self._items.get(item.item_id)
        if existing is not None:
            return existing
        self._items[item.item_id] = item
        self._persist()
        return item

    def decide(
        self,
        item_id: str,
        action: Action,
        actor: str,
        actor_type: ActorType = ActorType.HUMAN,
        note: str = "",
        details: dict[str, Any] | None = None,
    ) -> ReviewItem:
        if not actor.strip():
            raise ValueError("a decision must name who or what made it")
        item = self.get(item_id)
        item.decisions.append(
            Decision(action, actor.strip(), actor_type, now(), note, dict(details or {}))
        )
        self._persist()
        return item


class JsonReviewStore(ReviewStore):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        items = []
        if self.path.exists():
            items = [_item_from_json(d) for d in json.loads(self.path.read_text())["items"]]
        super().__init__(items)

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"items": [_item_to_json(i) for i in self.items()]}
        # Write then rename so a crash never leaves a half-written queue.
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        os.replace(tmp, self.path)


def _prov_to_json(p: Provenance) -> dict[str, str]:
    return {
        "source_type": p.source_type.value,
        "source_id": p.source_id,
        "source_url": p.source_url,
        "source_date": p.source_date.isoformat(),
    }


def _prov_from_json(d: dict[str, str]) -> Provenance:
    return Provenance(
        SourceType(d["source_type"]),
        d["source_id"],
        d["source_url"],
        date.fromisoformat(d["source_date"]),
    )


def _item_to_json(i: ReviewItem) -> dict[str, Any]:
    return {
        "item_id": i.item_id,
        "kind": i.kind.value,
        "subject": i.subject,
        "candidate_company_id": i.candidate_company_id,
        "score": i.score,
        "reasons": list(i.reasons),
        "evidence": [_prov_to_json(p) for p in i.evidence],
        "created_at": i.created_at.isoformat(),
        "decisions": [
            {
                "action": d.action.value,
                "actor": d.actor,
                "actor_type": d.actor_type.value,
                "at": d.at.isoformat(),
                "note": d.note,
                "details": d.details,
            }
            for d in i.decisions
        ],
    }


def _item_from_json(d: dict[str, Any]) -> ReviewItem:
    return ReviewItem(
        kind=ReviewKind(d["kind"]),
        subject=d["subject"],
        candidate_company_id=d["candidate_company_id"],
        score=d["score"],
        reasons=tuple(d["reasons"]),
        evidence=tuple(_prov_from_json(p) for p in d["evidence"]),
        created_at=datetime.fromisoformat(d["created_at"]),
        decisions=[
            Decision(
                Action(x["action"]),
                x["actor"],
                ActorType(x["actor_type"]),
                datetime.fromisoformat(x["at"]),
                x.get("note", ""),
                x.get("details", {}),
            )
            for x in d["decisions"]
        ],
    )
