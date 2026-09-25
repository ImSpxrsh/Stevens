from datetime import date

import pytest

from gauge.core.models import (
    EvidenceItem,
    EvidenceKind,
    NormalizedRecord,
    Provenance,
    SourceType,
)
from tests.factories import form_d, profile, sbir


def test_provenance_requires_a_public_url():
    with pytest.raises(ValueError):
        Provenance(SourceType.SEC_FORM_D, "abc", "not-a-url", date(2022, 1, 1))


def test_form_d_record_requires_form_d_facts():
    prov = Provenance(SourceType.SEC_FORM_D, "x", "https://www.sec.gov/x", date(2022, 1, 1))
    with pytest.raises(ValueError, match="form_d"):
        NormalizedRecord(provenance=prov, name="Acme")


def test_fact_evidence_must_cite_a_record():
    with pytest.raises(ValueError):
        EvidenceItem(claim="Raised $2M", kind=EvidenceKind.FACT)
    EvidenceItem(claim="Team size", kind=EvidenceKind.UNKNOWN)


def test_profile_keeps_multiple_sources_and_orders_by_date():
    later = form_d(filed=date(2023, 1, 1))
    earlier = form_d(filed=date(2021, 1, 1))
    award = sbir()
    p = profile(later, award, earlier)
    assert p.form_d_records == [earlier, later]
    assert p.sbir_records == [award]
    assert p.ciks == {"0001900001"}


def test_as_of_drops_future_records():
    old = form_d(filed=date(2022, 6, 1))
    new = form_d(filed=date(2023, 6, 1))
    p = profile(old, new).as_of(date(2022, 12, 31))
    assert p.records == [old]


def test_employee_count_uses_latest_award():
    p = profile(
        sbir(awarded=date(2021, 1, 1), employee_count=3),
        sbir(awarded=date(2022, 1, 1), employee_count=9),
    )
    count, source = p.employee_count()
    assert count == 9
    assert source.source_date == date(2022, 1, 1)
