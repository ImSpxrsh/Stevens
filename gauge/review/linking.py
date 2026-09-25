"""Minimal record-to-company linking that feeds the review queue.

This is the smallest linker the review tools need, not the merge engine in
#6. It applies two deterministic keys and sends everything else to review:

1. Same SEC company ID (CIK): merged automatically.
2. Same normalized name and same 5-digit postal code: merged automatically.
3. Similar name (or same name, different address): a review item is opened
   and the record stays in its own company until a reviewer approves.

Decisions already in the store are applied on every run, so approving an
item and re-running produces the merged profile, and a rejected match is
never proposed again.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from gauge.core.models import CompanyProfile, NormalizedRecord
from gauge.core.names import name_similarity, normalize_company_name, normalize_town
from gauge.review.models import ReviewItem, ReviewKind, ReviewStatus, now
from gauge.review.store import ReviewStore

FUZZY_REVIEW_THRESHOLD = 0.85


class LinkBasis(StrEnum):
    EXACT_CIK = "exact_cik"
    EXACT_NAME_POSTAL = "exact_name_postal"
    HUMAN_APPROVED = "human_approved"
    MODEL_APPROVED = "model_approved"
    NEW_COMPANY = "new_company"  # the record started its own company


@dataclass(frozen=True)
class RecordLink:
    record_key: str
    company_id: str
    basis: LinkBasis
    # Set when a fuzzy match was proposed for this record (any status).
    review_item_id: str | None = None


@dataclass
class LinkResult:
    profiles: dict[str, CompanyProfile] = field(default_factory=dict)
    links: dict[str, RecordLink] = field(default_factory=dict)

    def profile_for(self, record_key: str) -> CompanyProfile:
        return self.profiles[self.links[record_key].company_id]


def _postal5(rec: NormalizedRecord) -> str:
    return (rec.address.postal_code or "")[:5] if rec.address else ""


def _town(rec: NormalizedRecord) -> str:
    return normalize_town(rec.address.city) if rec.address else ""


def link_records(
    records: Iterable[NormalizedRecord],
    store: ReviewStore,
    *,
    fuzzy_threshold: float = FUZZY_REVIEW_THRESHOLD,
) -> LinkResult:
    result = LinkResult()
    ordered = sorted(records, key=lambda r: (r.source_date, r.key))

    def attach(rec: NormalizedRecord, company_id: str, basis: LinkBasis, item_id=None) -> None:
        profile = result.profiles.get(company_id)
        if profile is None:
            profile = result.profiles[company_id] = CompanyProfile(company_id, rec.name)
        profile.records.append(rec)
        result.links[rec.key] = RecordLink(rec.key, company_id, basis, item_id)

    for rec in ordered:
        if rec.cik:
            attach(rec, f"cik:{rec.cik}", LinkBasis.EXACT_CIK)

    for rec in ordered:
        if rec.cik:
            continue
        norm, postal = normalize_company_name(rec.name), _postal5(rec)
        exact = [
            p.company_id
            for p in result.profiles.values()
            if postal
            and any(
                normalize_company_name(r.name) == norm and _postal5(r) == postal for r in p.records
            )
        ]
        if len(exact) == 1:
            attach(rec, exact[0], LinkBasis.EXACT_NAME_POSTAL)
            continue

        candidate = _best_candidate(rec, result.profiles.values(), fuzzy_threshold)
        if candidate is None:
            attach(rec, f"rec:{rec.key}", LinkBasis.NEW_COMPANY)
            continue

        profile, score, reasons = candidate
        item = store.find(ReviewKind.RECORD_MATCH, rec.key, profile.company_id)
        if item is None:
            item = store.add(
                ReviewItem(
                    kind=ReviewKind.RECORD_MATCH,
                    subject=rec.key,
                    candidate_company_id=profile.company_id,
                    score=score,
                    reasons=reasons,
                    evidence=(rec.provenance, *(r.provenance for r in profile.records[:3])),
                    created_at=now(),
                )
            )
        if item.status is ReviewStatus.APPROVED:
            basis = LinkBasis.HUMAN_APPROVED if item.resolved_by_human else LinkBasis.MODEL_APPROVED
            attach(rec, profile.company_id, basis, item.item_id)
        else:
            attach(rec, f"rec:{rec.key}", LinkBasis.NEW_COMPANY, item.item_id)

    return result


def _best_candidate(
    rec: NormalizedRecord, profiles: Iterable[CompanyProfile], threshold: float
) -> tuple[CompanyProfile, float, tuple[str, ...]] | None:
    best: tuple[CompanyProfile, float, tuple[str, ...]] | None = None
    for profile in profiles:
        score = max(name_similarity(rec.name, r.name) for r in profile.records)
        if score < threshold:
            continue
        other = profile.records[0]
        reasons = [f"Name similarity {score:.2f}: {rec.name!r} vs {profile.name!r}."]
        postals = {_postal5(r) for r in profile.records} - {""}
        towns = {_town(r) for r in profile.records} - {""}
        if _postal5(rec) and _postal5(rec) in postals:
            reasons.append(f"Same postal code {_postal5(rec)}.")
        elif _postal5(rec) and postals:
            reasons.append(
                f"Different postal codes: {_postal5(rec)} vs {', '.join(sorted(postals))}."
            )
        if _town(rec) and _town(rec) in towns:
            reasons.append(f"Same town: {rec.address.city if rec.address else ''}.")
        if other.cik:
            reasons.append(f"Candidate has SEC company ID {other.cik}; this record has none.")
        if best is None or score > best[1]:
            best = (profile, score, tuple(reasons))
    return best
