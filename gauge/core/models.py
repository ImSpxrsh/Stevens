"""Core domain types shared by every Gauge module.

These types are intentionally small. The database schema (#28), the
source-adapter contract (#32), and the merge engine (#6) are expected to
extend them; everything downstream (classifier, program rules, review,
validation) reads companies only through these shapes.

Two rules hold throughout:

* Every public-record claim keeps its provenance (source type, id, URL, date).
* Facts from records, labels we infer, and gaps we cannot answer are kept
  apart (see ``EvidenceKind``).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from enum import StrEnum


class SourceType(StrEnum):
    SEC_FORM_D = "sec_form_d"
    SBIR_STTR = "sbir_sttr"
    NJEDA_ANNOUNCEMENT = "njeda_announcement"
    CSIT_ANNOUNCEMENT = "csit_announcement"
    USPTO_TRADEMARK = "uspto_trademark"


@dataclass(frozen=True)
class Provenance:
    """Where a record came from. Required on every normalized record."""

    source_type: SourceType
    source_id: str  # EDGAR accession number, SBIR award id, announcement URL hash, ...
    source_url: str
    source_date: date  # filing, award, or publication date

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("provenance requires a source_id")
        if not self.source_url.startswith(("http://", "https://")):
            raise ValueError(f"provenance requires an http(s) source_url, got {self.source_url!r}")

    @property
    def key(self) -> str:
        return f"{self.source_type}:{self.source_id}"


@dataclass(frozen=True)
class Address:
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None

    @property
    def in_new_jersey(self) -> bool:
        return (self.state or "").strip().upper() == "NJ"


@dataclass(frozen=True)
class FormDFacts:
    """The Form D fields Gauge uses. Item numbers refer to SEC Form D."""

    industry_group: str | None = None  # item 4, e.g. "Biotechnology", "Pooled Investment Fund"
    is_pooled_investment_fund: bool = False
    entity_type: str | None = None  # item 1, e.g. "Corporation", "Limited Partnership"
    jurisdiction_of_incorporation: str | None = None  # two-letter state code
    year_of_incorporation: int | None = None
    incorporated_within_five_years: bool | None = None
    revenue_range: str | None = None  # item 5 bucket, e.g. "No Revenues", "$1 - $1,000,000"
    total_offering_amount: float | None = None  # None means "Indefinite"
    total_amount_sold: float | None = None
    date_of_first_sale: date | None = None
    is_amendment: bool = False
    securities_offered: tuple[str, ...] = ()  # item 9, e.g. ("Equity",)


class SbirPhase(StrEnum):
    PHASE_I = "phase_i"
    PHASE_II = "phase_ii"
    FAST_TRACK = "fast_track"
    DIRECT_TO_PHASE_II = "direct_to_phase_ii"


@dataclass(frozen=True)
class SbirFacts:
    """The SBIR/STTR award fields Gauge uses (SBIR.gov award data)."""

    phase: SbirPhase
    program: str = "SBIR"  # "SBIR" or "STTR"
    agency: str | None = None  # e.g. "HHS", "DOD", "NSF"
    award_amount: float | None = None
    award_start: date | None = None
    award_end: date | None = None
    topic_title: str | None = None
    abstract: str | None = None
    employee_count: int | None = None  # "Number of Employees" reported at award time
    place_of_performance_state: str | None = None


@dataclass(frozen=True)
class NormalizedRecord:
    """One public record after source-specific parsing.

    Downstream code never sees raw payloads; it sees this.
    """

    provenance: Provenance
    name: str
    address: Address | None = None
    cik: str | None = None  # SEC company identifier; only Form D records carry it
    form_d: FormDFacts | None = None
    sbir: SbirFacts | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(f"record {self.provenance.key} has no company name")
        st = self.provenance.source_type
        if st is SourceType.SEC_FORM_D and self.form_d is None:
            raise ValueError(f"Form D record {self.provenance.key} is missing form_d facts")
        if st is SourceType.SBIR_STTR and self.sbir is None:
            raise ValueError(f"SBIR/STTR record {self.provenance.key} is missing sbir facts")

    @property
    def key(self) -> str:
        return self.provenance.key

    @property
    def source_date(self) -> date:
        return self.provenance.source_date


@dataclass
class CompanyProfile:
    """One canonical company with every record linked to it."""

    company_id: str
    name: str
    records: list[NormalizedRecord] = field(default_factory=list)

    def records_of(self, source_type: SourceType) -> list[NormalizedRecord]:
        return sorted(
            (r for r in self.records if r.provenance.source_type is source_type),
            key=lambda r: r.source_date,
        )

    @property
    def form_d_records(self) -> list[NormalizedRecord]:
        return self.records_of(SourceType.SEC_FORM_D)

    @property
    def sbir_records(self) -> list[NormalizedRecord]:
        return self.records_of(SourceType.SBIR_STTR)

    @property
    def ciks(self) -> set[str]:
        return {r.cik for r in self.records if r.cik}

    def latest_address(self) -> tuple[Address, Provenance] | None:
        dated = sorted(
            (r for r in self.records if r.address is not None), key=lambda r: r.source_date
        )
        if not dated:
            return None
        latest = dated[-1]
        assert latest.address is not None
        return latest.address, latest.provenance

    def has_new_jersey_address(self) -> bool:
        return any(r.address is not None and r.address.in_new_jersey for r in self.records)

    def employee_count(self) -> tuple[int, Provenance] | None:
        """Most recent employee count reported in any record, with its source."""
        counted = [r for r in self.sbir_records if r.sbir and r.sbir.employee_count is not None]
        if not counted:
            return None
        latest = counted[-1]
        assert latest.sbir is not None and latest.sbir.employee_count is not None
        return latest.sbir.employee_count, latest.provenance

    def as_of(self, cutoff: date) -> CompanyProfile:
        """The profile as it would have looked on ``cutoff``: later records removed.

        Backtests use this so no feature can see the future.
        """
        return replace(self, records=[r for r in self.records if r.source_date <= cutoff])


class EvidenceKind(StrEnum):
    FACT = "fact"  # established by a public record
    INFERRED = "inferred"  # a label Gauge derived (classifier, program rule)
    UNKNOWN = "unknown"  # a gap the public records cannot answer


@dataclass(frozen=True)
class EvidenceItem:
    """One claim on a company card. #8 owns the full evidence/certainty model."""

    claim: str
    kind: EvidenceKind
    source: Provenance | None = None
    value: str | None = None
    confidence: float | None = None
    limitations: str | None = None
    extracted_by: str | None = None  # model id when a language model extracted the value

    def __post_init__(self) -> None:
        if self.kind is EvidenceKind.FACT and self.source is None:
            raise ValueError(f"fact {self.claim!r} must cite a public record")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")
