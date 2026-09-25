"""NJEDA Life Sciences & Healthcare Fund (SSBCI).

NJEDA provides up to $10M of matching capital, at least 1:1 with private
money, invested through approved partner fund managers into NJ life-science
and healthcare companies raising Seed through Series C rounds.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from gauge.core.models import CompanyProfile
from gauge.programs.base import (
    Basis,
    CheckOutcome,
    CheckResult,
    Criterion,
    MatchResult,
    ProgramMatch,
    ProgramSource,
    decide,
    default_summary,
)

PROGRAM_ID = "njeda_life_sciences_healthcare_fund"
PROGRAM_NAME = "NJEDA Life Sciences & Healthcare Fund"
RULES_VERSION = "lshf-2025-10-28"
REVIEWED = date(2026, 9, 25)

PROGRAM_PAGE = ProgramSource(
    title="Life Sciences/Healthcare Fund, NJEDA",
    url="https://www.njeda.gov/lifescienceshealthcarefund/",
    reviewed_on=REVIEWED,
    effective=date(2025, 10, 28),
    note="Page last modified 2025-10-28.",
)
SSBCI_NOTICE = ProgramSource(
    title="SSBCI Life Science/Healthcare Fund, Notice of Investment Opportunity, NJEDA",
    url="https://www.njeda.gov/wp-content/uploads/2024/08/Life-Science-SSBCI-Notice-of-Investment-Opportunity.pdf",
    reviewed_on=REVIEWED,
    effective=date(2024, 8, 9),
    note="Defines qualifying NJ-based businesses, round-size limits, and prohibited businesses.",
)
SOURCES = (PROGRAM_PAGE, SSBCI_NOTICE)

MAX_EMPLOYEES = 750
MAX_ROUND_SIZE = 20_000_000  # no investments in rounds of $20M or more
ACTIVE_RAISE_WINDOW = timedelta(days=365)

HEALTH_INDUSTRY_GROUPS = frozenset(
    {"Biotechnology", "Pharmaceuticals", "Other Health Care", "Hospitals and Physicians"}
)
NON_HEALTH_INDUSTRY_GROUPS = frozenset(
    {
        "Restaurants",
        "Retailing",
        "Lodging and Conventions",
        "Tourism and Travel Services",
        "Airlines and Airports",
        "Residential",
        "Commercial",
        "Construction",
        "REITS and Finance",
        "Other Real Estate",
        "Commercial Banking",
        "Investing",
        "Investment Banking",
        "Pooled Investment Fund",
        "Oil and Gas",
        "Coal Mining",
    }
)
HEALTH_AGENCIES = frozenset({"HHS", "NIH", "CDC", "FDA"})
# Words in an SBIR topic or abstract that point at a life-science or health product.
_HEALTH_TERMS = re.compile(
    r"\b(therapeutic\w*|diagnos\w+|clinical|patient\w*|drug\w*|vaccin\w*|medical|"
    r"biomarker\w*|pharma\w*|disease\w*|cancer|oncolog\w*|health\w*|biomedical|"
    r"microbiome|regenerative)\b",
    re.IGNORECASE,
)

PARTNER_FUNDS = (
    "Tech Council Ventures: Seed to Series B; digital health, medical devices, biotech, "
    "healthcare IT",
    "Signet Healthcare Partners: Series B or C; pharma services, manufacturing, generics, "
    "research, medical devices, diagnostics, in the commercialization phase",
)


def _s(id: str, text: str, question: str, source: ProgramSource = PROGRAM_PAGE) -> Criterion:
    return Criterion(id, text, Basis.SCREENED, source, question)


def _a(id: str, text: str, source: ProgramSource = PROGRAM_PAGE) -> Criterion:
    return Criterion(id, text, Basis.ATTESTED, source, text)


NJ_LOCATION = _s(
    "nj_location",
    "Located in NJ: headquarters in NJ, or at least 50% of full-time employees live or work in NJ.",
    "Is the company headquartered in NJ, or do at least half of its full-time employees live "
    "or work in NJ?",
)
HEALTH_FOCUS = _s(
    "life_science_focus",
    "Primary focus is life sciences or healthcare.",
    "Is the company's primary focus a life-science or healthcare product?",
)
HEADCOUNT = _s(
    "headcount",
    f"No more than {MAX_EMPLOYEES} employees.",
    f"How many employees does the company have (maximum {MAX_EMPLOYEES})?",
)
ACTIVE_ROUND = _s(
    "active_round_under_20m",
    "Currently raising a round with a total size under $20M.",
    "Is the company raising now, and what is the total round size (must be under $20M)?",
    SSBCI_NOTICE,
)

ATTESTED = (
    _a("nj_registered", "Is a New Jersey registered business entity."),
    _a("round_stage", "The round is Seed through Series C.", SSBCI_NOTICE),
    _a(
        "partner_fund_and_match",
        "An approved partner fund manager invests, with at least 1:1 private matching capital.",
    ),
    _a(
        "first_ssbci_investment",
        "This is the company's first SSBCI investment and SSBCI funds into it stay under $20M.",
        SSBCI_NOTICE,
    ),
    _a(
        "not_prohibited_business",
        "Not an SSBCI-prohibited business (majority lending revenue, over one-third gambling "
        "revenue, speculative trading, pyramid sales, or activity illegal under federal law, "
        "including cannabis).",
        SSBCI_NOTICE,
    ),
)


def evaluate(profile: CompanyProfile, as_of: date) -> ProgramMatch:
    p = profile.as_of(as_of)
    checks = [
        _location_check(p),
        _health_focus_check(p),
        _headcount_check(p),
        _active_round_check(p, as_of),
    ]
    result = decide(checks)
    summary = default_summary(result, checks)
    if result is not MatchResult.NOT_A_MATCH:
        summary += " Partner fund managers: " + "; ".join(PARTNER_FUNDS) + "."
    return ProgramMatch(
        program_id=PROGRAM_ID,
        program_name=PROGRAM_NAME,
        result=result,
        summary=summary,
        checks=tuple(checks),
        confirm_before_applying=ATTESTED,
        sources=SOURCES,
        as_of=as_of,
        rules_version=RULES_VERSION,
    )


def _location_check(p: CompanyProfile) -> CheckResult:
    latest = p.latest_address()
    if latest is not None and latest[0].in_new_jersey:
        return CheckResult(
            NJ_LOCATION,
            CheckOutcome.PASS,
            "Most recent record lists a New Jersey address.",
            (latest[1],),
            needs_confirmation=True,  # a filing address is not proof of headquarters
        )
    return CheckResult(
        NJ_LOCATION,
        CheckOutcome.UNKNOWN,
        "Most recent record does not list a New Jersey address; the 50%-of-employees route "
        "cannot be checked from public records.",
        (latest[1],) if latest else (),
    )


def _health_focus_check(p: CompanyProfile) -> CheckResult:
    if p.form_d_records:
        latest = p.form_d_records[-1]
        group = latest.form_d.industry_group if latest.form_d else None
        if group in HEALTH_INDUSTRY_GROUPS:
            return CheckResult(
                HEALTH_FOCUS,
                CheckOutcome.PASS,
                f"Latest Form D industry group is {group}.",
                (latest.provenance,),
            )
        if group in NON_HEALTH_INDUSTRY_GROUPS:
            return CheckResult(
                HEALTH_FOCUS,
                CheckOutcome.FAIL,
                f"Latest Form D industry group is {group}.",
                (latest.provenance,),
            )

    health_awards = [
        r
        for r in p.sbir_records
        if r.sbir
        and (
            (r.sbir.agency or "").upper() in HEALTH_AGENCIES
            or _HEALTH_TERMS.search(f"{r.sbir.topic_title or ''} {r.sbir.abstract or ''}")
        )
    ]
    if health_awards:
        agencies = sorted({r.sbir.agency or "unknown agency" for r in health_awards if r.sbir})
        return CheckResult(
            HEALTH_FOCUS,
            CheckOutcome.PASS,
            f"SBIR/STTR award(s) from {', '.join(agencies)} with health or life-science topics.",
            tuple(r.provenance for r in health_awards),
            needs_confirmation=True,
        )
    return CheckResult(
        HEALTH_FOCUS,
        CheckOutcome.UNKNOWN,
        "Records do not show a life-science or healthcare focus.",
        tuple(r.provenance for r in p.records),
    )


def _headcount_check(p: CompanyProfile) -> CheckResult:
    headcount = p.employee_count()
    if headcount is None:
        return CheckResult(HEADCOUNT, CheckOutcome.UNKNOWN, "No record reports headcount.")
    count, prov = headcount
    return CheckResult(
        HEADCOUNT,
        CheckOutcome.PASS if count <= MAX_EMPLOYEES else CheckOutcome.FAIL,
        f"Latest record reports {count} employees.",
        (prov,),
    )


def _active_round_check(p: CompanyProfile, as_of: date) -> CheckResult:
    recent = [r for r in p.form_d_records if as_of - r.source_date <= ACTIVE_RAISE_WINDOW]
    if not recent:
        return CheckResult(
            ACTIVE_ROUND,
            CheckOutcome.UNKNOWN,
            "No Form D filed in the last 12 months.",
            tuple(r.provenance for r in p.form_d_records),
        )
    latest = recent[-1]
    amount = latest.form_d.total_offering_amount if latest.form_d else None
    if amount is None:
        return CheckResult(
            ACTIVE_ROUND,
            CheckOutcome.UNKNOWN,
            f"Form D filed {latest.source_date.isoformat()} lists an indefinite offering size.",
            (latest.provenance,),
        )
    return CheckResult(
        ACTIVE_ROUND,
        CheckOutcome.PASS if amount < MAX_ROUND_SIZE else CheckOutcome.FAIL,
        f"Form D filed {latest.source_date.isoformat()} lists a ${amount:,.0f} offering.",
        (latest.provenance,),
    )
