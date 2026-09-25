"""Builders for normalized records and profiles used across the test suite.

All company names here are fictional.
"""

from __future__ import annotations

from datetime import date
from itertools import count

from gauge.core.models import (
    Address,
    CompanyProfile,
    FormDFacts,
    NormalizedRecord,
    Provenance,
    SbirFacts,
    SbirPhase,
    SourceType,
)

_ids = count(1)

NJ_ADDRESS = Address(street="1 Castle Point Ter", city="Hoboken", state="NJ", postal_code="07030")


def form_d(
    name: str = "Acme Robotics, Inc.",
    *,
    cik: str | None = "0001900001",
    filed: date = date(2022, 6, 1),
    address: Address | None = NJ_ADDRESS,
    **facts: object,
) -> NormalizedRecord:
    n = next(_ids)
    defaults: dict[str, object] = {
        "industry_group": "Other Technology",
        "entity_type": "Corporation",
        "jurisdiction_of_incorporation": "DE",
        "incorporated_within_five_years": True,
        "revenue_range": "Decline to Disclose",
        "total_offering_amount": 2_000_000.0,
        "total_amount_sold": 1_500_000.0,
        "securities_offered": ("Equity",),
    }
    defaults.update(facts)
    return NormalizedRecord(
        provenance=Provenance(
            SourceType.SEC_FORM_D,
            f"0001900001-22-{n:06d}",
            f"https://www.sec.gov/Archives/edgar/data/{cik or 0}/{n:06d}.xml",
            filed,
        ),
        name=name,
        address=address,
        cik=cik,
        form_d=FormDFacts(**defaults),  # type: ignore[arg-type]
    )


def sbir(
    name: str = "Acme Robotics LLC",
    *,
    awarded: date = date(2022, 3, 1),
    address: Address | None = NJ_ADDRESS,
    **facts: object,
) -> NormalizedRecord:
    n = next(_ids)
    defaults: dict[str, object] = {
        "phase": SbirPhase.PHASE_I,
        "agency": "NSF",
        "award_amount": 275_000.0,
        "award_start": awarded,
        "award_end": date(awarded.year + 1, awarded.month, 1),
        "topic_title": "Autonomous inspection robots",
        "employee_count": 6,
    }
    defaults.update(facts)
    return NormalizedRecord(
        provenance=Provenance(
            SourceType.SBIR_STTR,
            f"SBIR-{n:06d}",
            f"https://www.sbir.gov/awards/{n:06d}",
            awarded,
        ),
        name=name,
        address=address,
        form_d=None,
        sbir=SbirFacts(**defaults),  # type: ignore[arg-type]
    )


def profile(*records: NormalizedRecord, company_id: str | None = None) -> CompanyProfile:
    assert records, "a profile needs at least one record"
    return CompanyProfile(
        company_id=company_id or f"co-{next(_ids)}",
        name=records[0].name,
        records=list(records),
    )
