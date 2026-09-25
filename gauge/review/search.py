"""Search company profiles by name, source ID, or town."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from gauge.core.models import CompanyProfile
from gauge.core.names import name_similarity, normalize_company_name, normalize_town

MIN_NAME_SIMILARITY = 0.6


@dataclass(frozen=True)
class SearchHit:
    profile: CompanyProfile
    score: float
    matched_on: str


def search_companies(
    profiles: Iterable[CompanyProfile],
    query: str = "",
    *,
    town: str | None = None,
    limit: int = 25,
) -> list[SearchHit]:
    """Find companies whose name, SEC company ID, or any linked record ID matches ``query``.

    An empty query lists every company (optionally filtered by town).
    """
    q = query.strip()
    q_norm = normalize_company_name(q) if q else ""
    town_norm = normalize_town(town)
    hits: list[SearchHit] = []
    for p in profiles:
        if town_norm and town_norm not in _towns(p):
            continue
        hit = _match(p, q, q_norm)
        if hit is not None:
            hits.append(hit)
    hits.sort(key=lambda h: (-h.score, h.profile.name.lower(), h.profile.company_id))
    return hits[:limit]


def _towns(p: CompanyProfile) -> set[str]:
    return {normalize_town(r.address.city) for r in p.records if r.address and r.address.city}


def _match(p: CompanyProfile, q: str, q_norm: str) -> SearchHit | None:
    if not q:
        return SearchHit(p, 1.0, "all")
    if q in p.ciks or q == p.company_id:
        return SearchHit(p, 1.0, "sec company id" if q in p.ciks else "company id")
    if any(q in (r.provenance.source_id, r.key) for r in p.records):
        return SearchHit(p, 1.0, "source record id")
    names = {r.name for r in p.records} | {p.name}
    if q_norm and any(q_norm in normalize_company_name(n) for n in names):
        return SearchHit(p, 0.9, "name")
    best = max(name_similarity(q, n) for n in names)
    if best >= MIN_NAME_SIMILARITY:
        return SearchHit(p, round(best * 0.9, 3), "similar name")
    return None


def describe(p: CompanyProfile) -> list[str]:
    """Human-readable summary: identifiers, towns, and every linked record."""
    lines = [f"{p.name}  [{p.company_id}]"]
    if p.ciks:
        lines.append("  SEC company IDs: " + ", ".join(sorted(p.ciks)))
    towns = sorted({r.address.city for r in p.records if r.address and r.address.city})
    if towns:
        lines.append("  Towns: " + ", ".join(towns))
    for r in sorted(p.records, key=lambda r: r.source_date):
        lines.append(
            f"  - {r.provenance.source_type.value} {r.provenance.source_id} "
            f"{r.source_date.isoformat()} {r.name!r} {r.provenance.source_url}"
        )
    return lines
