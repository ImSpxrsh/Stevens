"""Company search, duplicate detection, and the manual review queue.

A fuzzy or uncertain match is never merged or alerted on until it is
reviewed; every decision records who or what made it.
"""

from gauge.review.gate import AlertGate, alert_gate, auto_alert_allowed
from gauge.review.linking import LinkBasis, LinkResult, RecordLink, link_records
from gauge.review.models import Action, ActorType, ReviewItem, ReviewKind, ReviewStatus
from gauge.review.store import JsonReviewStore, ReviewStore

__all__ = [
    "Action",
    "ActorType",
    "AlertGate",
    "JsonReviewStore",
    "LinkBasis",
    "LinkResult",
    "RecordLink",
    "ReviewItem",
    "ReviewKind",
    "ReviewStatus",
    "ReviewStore",
    "alert_gate",
    "auto_alert_allowed",
    "link_records",
]
