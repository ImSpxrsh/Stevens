"""Whether a record may drive an alert about a company.

Only an exact SEC company ID match alerts automatically. A match a person
approved may alert. Everything else waits for review, and a rejected match
never alerts. #15 (alerts) should call ``alert_gate`` before firing.
"""

from __future__ import annotations

from enum import StrEnum

from gauge.review.linking import LinkBasis, LinkResult
from gauge.review.models import ReviewKind, ReviewStatus
from gauge.review.store import ReviewStore


class AlertGate(StrEnum):
    AUTOMATIC = "automatic"
    HUMAN_REVIEWED = "human_reviewed"
    HOLD_FOR_REVIEW = "hold_for_review"
    BLOCKED = "blocked"


def alert_gate(
    record_key: str, company_id: str, linking: LinkResult, store: ReviewStore
) -> tuple[AlertGate, str]:
    link = linking.links.get(record_key)
    if link is None:
        return AlertGate.BLOCKED, "Record is not linked to any company."

    if link.company_id != company_id:
        item = store.find(ReviewKind.RECORD_MATCH, record_key, company_id)
        if item is not None and item.status is ReviewStatus.REJECTED:
            return AlertGate.BLOCKED, f"Match was rejected in review {item.item_id}."
        if item is not None:
            return AlertGate.HOLD_FOR_REVIEW, f"Match awaits review {item.item_id}."
        return AlertGate.BLOCKED, "Record belongs to a different company."

    match link.basis:
        case LinkBasis.EXACT_CIK:
            return AlertGate.AUTOMATIC, "Exact SEC company ID match."
        case LinkBasis.HUMAN_APPROVED:
            return AlertGate.HUMAN_REVIEWED, f"A person approved review {link.review_item_id}."
        case LinkBasis.MODEL_APPROVED:
            return (
                AlertGate.HOLD_FOR_REVIEW,
                "Only a model approved this match; a person must confirm before alerting.",
            )
        case _:
            return (
                AlertGate.HOLD_FOR_REVIEW,
                "Identity is not established by an SEC company ID.",
            )


def auto_alert_allowed(
    record_key: str, company_id: str, linking: LinkResult, store: ReviewStore
) -> bool:
    return alert_gate(record_key, company_id, linking, store)[0] is AlertGate.AUTOMATIC
