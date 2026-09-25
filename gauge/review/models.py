"""Review items for uncertain merges and fuzzy matches, with an append-only
decision log so every resolution records who or what made it."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from gauge.core.models import Provenance


class ReviewKind(StrEnum):
    # A record might belong to an existing company; not merged until reviewed.
    RECORD_MATCH = "record_match"
    # Two existing company profiles might be the same company.
    DUPLICATE_COMPANIES = "duplicate_companies"


class ReviewStatus(StrEnum):
    OPEN = "open"
    APPROVED = "approved"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"


class Action(StrEnum):
    APPROVE_MERGE = "approve_merge"
    REJECT_MERGE = "reject_merge"
    LEAVE_UNCERTAIN = "leave_uncertain"


class ActorType(StrEnum):
    HUMAN = "human"
    MODEL = "model"
    SYSTEM = "system"


_STATUS_FOR_ACTION = {
    Action.APPROVE_MERGE: ReviewStatus.APPROVED,
    Action.REJECT_MERGE: ReviewStatus.REJECTED,
    Action.LEAVE_UNCERTAIN: ReviewStatus.UNCERTAIN,
}


@dataclass(frozen=True)
class Decision:
    action: Action
    actor: str  # a person's name, a model id, or a system component
    actor_type: ActorType
    at: datetime
    note: str = ""
    # Structured audit data, e.g. a model's rationale and the evidence it saw.
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> ReviewStatus:
        return _STATUS_FOR_ACTION[self.action]


@dataclass
class ReviewItem:
    kind: ReviewKind
    subject: str  # record key for RECORD_MATCH, company id for DUPLICATE_COMPANIES
    candidate_company_id: str
    score: float
    reasons: tuple[str, ...]
    evidence: tuple[Provenance, ...]
    created_at: datetime
    decisions: list[Decision] = field(default_factory=list)

    @property
    def item_id(self) -> str:
        return review_item_id(self.kind, self.subject, self.candidate_company_id)

    @property
    def status(self) -> ReviewStatus:
        return self.decisions[-1].status if self.decisions else ReviewStatus.OPEN

    @property
    def resolved_by_human(self) -> bool:
        return bool(self.decisions) and self.decisions[-1].actor_type is ActorType.HUMAN


def review_item_id(kind: ReviewKind, subject: str, candidate_company_id: str) -> str:
    digest = hashlib.sha256(f"{kind}|{subject}|{candidate_company_id}".encode()).hexdigest()
    return f"rv_{digest[:12]}"


def now() -> datetime:
    return datetime.now(UTC)
