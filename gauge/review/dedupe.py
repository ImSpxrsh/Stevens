"""Find company profiles that may be duplicates and merge the approved ones."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import replace

from gauge.core.models import CompanyProfile
from gauge.core.names import name_similarity, normalize_company_name
from gauge.review.models import ReviewItem, ReviewKind, ReviewStatus, now
from gauge.review.store import ReviewStore

DUPLICATE_THRESHOLD = 0.85
# Common words that should not put two names in the same comparison block.
_BLOCKING_STOPWORDS = frozenset({"and", "of", "the", "group", "labs", "technologies", "health"})


def find_duplicate_companies(
    profiles: Iterable[CompanyProfile],
    store: ReviewStore,
    *,
    threshold: float = DUPLICATE_THRESHOLD,
) -> list[ReviewItem]:
    """Open a review item for each likely-duplicate pair of profiles.

    Pairs with two different SEC company IDs are skipped: they are separate
    SEC registrants. Only names sharing a word are compared, so this stays
    fast on large company lists.
    """
    by_id = {p.company_id: p for p in profiles}
    blocks: dict[str, set[str]] = defaultdict(set)
    for p in by_id.values():
        for token in set(normalize_company_name(p.name).split()) - _BLOCKING_STOPWORDS:
            blocks[token].add(p.company_id)

    pairs = {tuple(sorted((a, b))) for ids in blocks.values() for a in ids for b in ids if a < b}
    opened: list[ReviewItem] = []
    for a_id, b_id in sorted(pairs):
        a, b = by_id[a_id], by_id[b_id]
        if a.ciks and b.ciks and a.ciks.isdisjoint(b.ciks):
            continue
        score = name_similarity(a.name, b.name)
        if score < threshold:
            continue
        item = store.find(ReviewKind.DUPLICATE_COMPANIES, a_id, b_id)
        if item is None:
            item = store.add(
                ReviewItem(
                    kind=ReviewKind.DUPLICATE_COMPANIES,
                    subject=a_id,
                    candidate_company_id=b_id,
                    score=score,
                    reasons=(f"Name similarity {score:.2f}: {a.name!r} vs {b.name!r}.",),
                    evidence=tuple(r.provenance for r in (*a.records[:2], *b.records[:2])),
                    created_at=now(),
                )
            )
        if item.status is ReviewStatus.OPEN:
            opened.append(item)
    return opened


def merge_approved_duplicates(
    profiles: Mapping[str, CompanyProfile], store: ReviewStore
) -> dict[str, CompanyProfile]:
    """Merge profiles joined by approved duplicate reviews.

    The surviving id prefers an SEC company ID (``cik:``) and is otherwise the
    smallest id, so merges are deterministic.
    """
    parent = {cid: cid for cid in profiles}

    def root(cid: str) -> str:
        while parent[cid] != cid:
            parent[cid] = parent[parent[cid]]
            cid = parent[cid]
        return cid

    for item in store.items(ReviewStatus.APPROVED):
        if item.kind is not ReviewKind.DUPLICATE_COMPANIES:
            continue
        a, b = item.subject, item.candidate_company_id
        if a in parent and b in parent:
            ra, rb = root(a), root(b)
            if ra != rb:
                keep, drop = sorted((ra, rb), key=lambda c: (not c.startswith("cik:"), c))
                parent[drop] = keep

    merged: dict[str, CompanyProfile] = {}
    for cid, profile in sorted(profiles.items()):
        r = root(cid)
        if r not in merged:
            merged[r] = replace(profiles[r], records=list(profiles[r].records))
        if cid != r:
            merged[r].records.extend(profile.records)
    return merged
