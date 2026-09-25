"""Hard exclusion rules: records that are never startup discoveries.

These run before the model. They only fire on structured data (Form D
fields, headcount, a supplied list of public-company CIKs) plus two narrow
fund-name patterns, so a company cannot be excluded because its name happens
to contain a word like "fund".
"""

from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from gauge.core.models import CompanyProfile, Provenance

FUND_INDUSTRY_GROUPS = frozenset({"Pooled Investment Fund", "Investing"})
REAL_ESTATE_INDUSTRY_GROUPS = frozenset(
    {"REITS and Finance", "Residential", "Commercial", "Construction", "Other Real Estate"}
)
ESTABLISHED_REVENUE_RANGES = frozenset({"$25,000,001 - $100,000,000", "Over $100,000,000"})
ESTABLISHED_MIN_AGE_YEARS = 20
ESTABLISHED_MIN_HEADCOUNT = 500

# "Garden State Fund II", "Acme Opportunity Fund, L.P.", "Beacon Capital Partners LP"
_FUND_NAME = re.compile(
    r"\bfund\s+(?:[ivx]+|\d+)\b|\bfund\b.*\bl\.?\s?p\.?$|\b(?:capital|venture)\s+partners\b.*\bl\.?\s?p\.?$",
    re.IGNORECASE,
)


class ExclusionReason(StrEnum):
    FUND = "fund"
    REAL_ESTATE = "real_estate"
    PUBLIC_COMPANY = "public_company"
    ESTABLISHED = "established_firm"


@dataclass(frozen=True)
class Exclusion:
    reason: ExclusionReason
    explanation: str
    source: Provenance | None


def hard_exclusion(
    profile: CompanyProfile,
    as_of: date,
    public_ciks: Collection[str] = (),
) -> Exclusion | None:
    """Return the first rule that excludes this company, or None."""
    p = profile.as_of(as_of)

    for rec in p.form_d_records:
        fd = rec.form_d
        assert fd is not None
        if fd.is_pooled_investment_fund or fd.industry_group in FUND_INDUSTRY_GROUPS:
            return Exclusion(
                ExclusionReason.FUND,
                f"Form D lists the issuer as {fd.industry_group or 'a pooled investment fund'}.",
                rec.provenance,
            )
        if fd.industry_group in REAL_ESTATE_INDUSTRY_GROUPS:
            return Exclusion(
                ExclusionReason.REAL_ESTATE,
                f"Form D industry group is real estate ({fd.industry_group}).",
                rec.provenance,
            )

    for rec in p.records:
        if _FUND_NAME.search(rec.name.strip()):
            return Exclusion(
                ExclusionReason.FUND,
                f"Record name {rec.name!r} follows a fund naming pattern.",
                rec.provenance,
            )

    public = p.ciks & set(public_ciks)
    if public:
        cik = sorted(public)[0]
        source = next(r.provenance for r in p.records if r.cik == cik)
        return Exclusion(
            ExclusionReason.PUBLIC_COMPANY,
            f"SEC company ID {cik} belongs to a publicly traded company.",
            source,
        )

    if p.form_d_records:
        latest = p.form_d_records[-1]
        fd = latest.form_d
        assert fd is not None
        if fd.revenue_range in ESTABLISHED_REVENUE_RANGES:
            return Exclusion(
                ExclusionReason.ESTABLISHED,
                f"Latest Form D reports revenue of {fd.revenue_range}.",
                latest.provenance,
            )
        years = [r.form_d.year_of_incorporation for r in p.form_d_records if r.form_d]
        known = [y for y in years if y]
        if known and as_of.year - min(known) >= ESTABLISHED_MIN_AGE_YEARS:
            return Exclusion(
                ExclusionReason.ESTABLISHED,
                f"Form D reports incorporation in {min(known)}, "
                f"{as_of.year - min(known)} years before {as_of.isoformat()}.",
                latest.provenance,
            )

    headcount = p.employee_count()
    if headcount is not None and headcount[0] >= ESTABLISHED_MIN_HEADCOUNT:
        return Exclusion(
            ExclusionReason.ESTABLISHED,
            f"Latest reported headcount is {headcount[0]}.",
            headcount[1],
        )

    return None
