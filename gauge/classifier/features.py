"""Transparent features for the likely-startup model.

Every feature is a 0/1 indicator read from Form D or SBIR/STTR records dated
on or before ``as_of``, so a partner can check each one against the filing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from gauge.core.models import CompanyProfile, Provenance, SbirPhase

# Form D item 4 industry groups that indicate a technology or life-science business.
TECH_INDUSTRY_GROUPS = frozenset(
    {
        "Biotechnology",
        "Pharmaceuticals",
        "Other Health Care",
        "Computers",
        "Telecommunications",
        "Other Technology",
        "Energy Conservation",
        "Environmental Services",
        "Other Energy",
    }
)

# Form D item 5 revenue buckets above $1M.
REVENUE_OVER_1M = frozenset(
    {
        "$1,000,001 - $5,000,000",
        "$5,000,001 - $25,000,000",
        "$25,000,001 - $100,000,000",
        "Over $100,000,000",
    }
)

FEATURE_DESCRIPTIONS: dict[str, str] = {
    "incorporated_within_5y": "Form D says the company was incorporated within the last five years",
    "incorporated_over_5y": "Form D says the company was incorporated more than five years ago",
    "no_revenue": "Form D reports no revenues",
    "revenue_over_1m": "Form D reports revenue above $1M",
    "tech_industry": "Form D industry group is technology, life sciences, or clean energy",
    "equity_offering": "Form D offering includes equity",
    "offering_under_10m": "Largest Form D offering is under $10M",
    "sbir_phase_i": "Has a federal SBIR/STTR Phase I award",
    "sbir_phase_ii": "Has a federal SBIR/STTR Phase II award",
    "small_team": "Latest reported headcount is 50 or fewer",
    "large_team": "Latest reported headcount is over 100",
    "first_record_recent": "First public record is within the last three years",
}

FEATURE_NAMES: tuple[str, ...] = tuple(FEATURE_DESCRIPTIONS)


@dataclass(frozen=True)
class FeatureVector:
    values: dict[str, float]
    # Which records set each nonzero feature, so explanations can cite them.
    sources: dict[str, tuple[Provenance, ...]]


def extract_features(profile: CompanyProfile, as_of: date) -> FeatureVector:
    p = profile.as_of(as_of)
    values = dict.fromkeys(FEATURE_NAMES, 0.0)
    sources: dict[str, list[Provenance]] = {name: [] for name in FEATURE_NAMES}

    def mark(name: str, prov: Provenance) -> None:
        values[name] = 1.0
        sources[name].append(prov)

    for rec in p.form_d_records:
        fd = rec.form_d
        assert fd is not None
        age = as_of.year - fd.year_of_incorporation if fd.year_of_incorporation else None
        if fd.incorporated_within_five_years is True or (age is not None and age <= 5):
            mark("incorporated_within_5y", rec.provenance)
        elif fd.incorporated_within_five_years is False or (age is not None and age > 5):
            mark("incorporated_over_5y", rec.provenance)
        if fd.industry_group in TECH_INDUSTRY_GROUPS:
            mark("tech_industry", rec.provenance)
        if any(s.lower() == "equity" for s in fd.securities_offered):
            mark("equity_offering", rec.provenance)

    # Revenue and offering size describe the company now, so use the latest filing.
    if p.form_d_records:
        latest = p.form_d_records[-1]
        fd = latest.form_d
        assert fd is not None
        if fd.revenue_range == "No Revenues":
            mark("no_revenue", latest.provenance)
        elif fd.revenue_range in REVENUE_OVER_1M:
            mark("revenue_over_1m", latest.provenance)
        amounts = [
            (r.form_d.total_offering_amount, r.provenance)
            for r in p.form_d_records
            if r.form_d and r.form_d.total_offering_amount is not None
        ]
        if amounts and max(amount for amount, _ in amounts) < 10_000_000:
            mark("offering_under_10m", amounts[-1][1])

    for rec in p.sbir_records:
        assert rec.sbir is not None
        if rec.sbir.phase in (SbirPhase.PHASE_I, SbirPhase.FAST_TRACK):
            mark("sbir_phase_i", rec.provenance)
        if rec.sbir.phase in (
            SbirPhase.PHASE_II,
            SbirPhase.FAST_TRACK,
            SbirPhase.DIRECT_TO_PHASE_II,
        ):
            mark("sbir_phase_ii", rec.provenance)

    headcount = p.employee_count()
    if headcount is not None:
        count, prov = headcount
        if count <= 50:
            mark("small_team", prov)
        elif count > 100:
            mark("large_team", prov)

    if p.records:
        first = min(p.records, key=lambda r: r.source_date)
        if (as_of - first.source_date).days <= 3 * 365:
            mark("first_record_recent", first.provenance)

    return FeatureVector(values=values, sources={k: tuple(v) for k, v in sources.items()})
