"""New Jersey Angel Investor Tax Credit: is the company a qualifying
"emerging technology business" for its investors?

The program changed on January 1, 2026 (headcount cap cut from 225 to 150,
base credit raised from 20% to 35%). Both versions are encoded and picked by
the evaluation date, so backtests on older snapshots use the rules in force
at the time.
"""

from __future__ import annotations

from dataclasses import dataclass
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

PROGRAM_ID = "nj_angel_investor_tax_credit"
PROGRAM_NAME = "NJ Angel Investor Tax Credit"
REVIEWED = date(2026, 9, 25)

PROGRAM_PAGE = ProgramSource(
    title="Angel Investor Tax Credit Program, NJEDA",
    url="https://www.njeda.gov/angeltaxcredit/",
    reviewed_on=REVIEWED,
    note="Page last modified 2026-08-20; states the 150-employee cap and 35%/40% credit.",
)
CHANGE_NOTICE = ProgramSource(
    title="NJ Angel Investor Tax Credit 2026 Updates, Withum (secondary source)",
    url="https://www.withum.com/resources/nj-angel-investor-tax-credit-2026-updates-bigger-benefits-for-digital-health-investors/",
    reviewed_on=REVIEWED,
    effective=date(2026, 1, 1),
    note="Dates the change to 2026-01-01; the NJEDA page does not state an effective date.",
)
PRIOR_PAGE = ProgramSource(
    title="Angel Investor Tax Credit Program (ERA update), NJEDA",
    url="https://www.njeda.gov/angel-tax-credit-program-era-update/",
    reviewed_on=REVIEWED,
    note="Pre-2026 rules: fewer than 225 employees, 20% credit (25% with bonus), $500,000 cap.",
)
PRIOR_TREASURY = ProgramSource(
    title="Notice: Angel Investor Tax Credit Increase, NJ Division of Taxation",
    url="https://www.nj.gov/treasury/taxation/noticeangelinvestortaxcreditincrease-cbt.shtml",
    reviewed_on=REVIEWED,
)

ELIGIBLE_TECHNOLOGIES = (
    "advanced computing",
    "advanced materials",
    "biotechnology",
    "electronic devices",
    "information technology",
    "life sciences",
    "medical devices",
    "mobile communications",
    "renewable energy technology",
    "carbon footprint reduction technology",
)

# Form D industry groups that map onto the eligible technology list.
ELIGIBLE_INDUSTRY_GROUPS = frozenset(
    {
        "Biotechnology",
        "Pharmaceuticals",
        "Computers",
        "Telecommunications",
        "Other Technology",
        "Energy Conservation",
    }
)
# Industry groups whose primary business cannot be an eligible technology.
INELIGIBLE_INDUSTRY_GROUPS = frozenset(
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
        "Insurance",
        "Investing",
        "Investment Banking",
        "Pooled Investment Fund",
    }
)

APPLICATION_WINDOW = timedelta(days=183)  # six months from the date of investment


@dataclass(frozen=True)
class RuleVersion:
    version: str
    effective_from: date | None
    effective_to: date | None
    employee_cap: int  # company must employ fewer than this many full-time employees
    credit: str
    sources: tuple[ProgramSource, ...]


V2026 = RuleVersion(
    version="angel-2026-01-01",
    effective_from=date(2026, 1, 1),
    effective_to=None,
    employee_cap=150,
    credit="35% refundable credit (40% for certified M/WBEs or Opportunity Zone / "
    "New Markets Tax Credit tracts)",
    sources=(PROGRAM_PAGE, CHANGE_NOTICE),
)
PRE_2026 = RuleVersion(
    version="angel-pre-2026",
    effective_from=None,  # start date of this version was not verified
    effective_to=date(2025, 12, 31),
    employee_cap=225,
    credit="20% refundable credit (25% with bonus), capped at $500,000",
    sources=(PRIOR_PAGE, PRIOR_TREASURY),
)
VERSIONS = (V2026, PRE_2026)


def rule_version(as_of: date) -> RuleVersion:
    for v in VERSIONS:
        if (v.effective_from is None or as_of >= v.effective_from) and (
            v.effective_to is None or as_of <= v.effective_to
        ):
            return v
    raise ValueError(f"no Angel Investor Tax Credit rules cover {as_of}")


def _criteria(v: RuleVersion) -> dict[str, Criterion]:
    src = v.sources[0]
    return {
        "headcount": Criterion(
            "headcount",
            f"Employs fewer than {v.employee_cap} full-time employees.",
            Basis.SCREENED,
            src,
            f"How many full-time employees does the company have (must be under {v.employee_cap})?",
        ),
        "nj_presence": Criterion(
            "nj_presence",
            "Does business, employs, owns capital or property, or maintains an office in NJ.",
            Basis.SCREENED,
            src,
            "Does the company maintain an office or do business in New Jersey?",
        ),
        "eligible_technology": Criterion(
            "eligible_technology",
            "Primary business is an eligible technology: " + ", ".join(ELIGIBLE_TECHNOLOGIES) + ".",
            Basis.SCREENED,
            src,
            "Which eligible technology is the company's primary business?",
        ),
    }


def _attested(v: RuleVersion) -> tuple[Criterion, ...]:
    src = v.sources[0]

    def a(id: str, text: str) -> Criterion:
        return Criterion(id, text, Basis.ATTESTED, src, text)

    return (
        a("nj_workforce_75", "At least 75% of full-time employees work in New Jersey."),
        a("one_full_time_employee", "Has at least one full-time employee."),
        a(
            "nj_technology_activity",
            "Incurs qualified research expenses, runs pilot-scale manufacturing, or "
            "commercializes an eligible technology in New Jersey.",
        ),
        a("not_cannabis", "Not a cannabis licensee (cannabis businesses are ineligible)."),
        a(
            "qualified_investment",
            "Investor's cash goes directly to the company, is non-refundable, and is held "
            "at least two calendar years.",
        ),
        a(
            "application_window",
            "Investor applies to NJEDA within six months of the investment date.",
        ),
    )


def evaluate(profile: CompanyProfile, as_of: date) -> ProgramMatch:
    v = rule_version(as_of)
    crit = _criteria(v)
    p = profile.as_of(as_of)
    checks: list[CheckResult] = []

    headcount = p.employee_count()
    if headcount is None:
        checks.append(
            CheckResult(crit["headcount"], CheckOutcome.UNKNOWN, "No record reports headcount.")
        )
    else:
        count, prov = headcount
        checks.append(
            CheckResult(
                crit["headcount"],
                CheckOutcome.PASS if count < v.employee_cap else CheckOutcome.FAIL,
                f"Latest record reports {count} employees (cap: fewer than {v.employee_cap}).",
                (prov,),
            )
        )

    nj = [r for r in p.records if r.address is not None and r.address.in_new_jersey]
    checks.append(
        CheckResult(
            crit["nj_presence"],
            CheckOutcome.PASS,
            "Record(s) list a New Jersey address.",
            tuple(r.provenance for r in nj),
        )
        if nj
        else CheckResult(
            crit["nj_presence"], CheckOutcome.UNKNOWN, "No record lists a New Jersey address."
        )
    )

    checks.append(_eligible_technology_check(crit["eligible_technology"], p))

    result = decide(checks)
    summary = default_summary(result, checks)
    if result is not MatchResult.NOT_A_MATCH:
        summary += f" Investors may qualify for a {v.credit}."
        recent = [r for r in p.form_d_records if as_of - r.source_date <= APPLICATION_WINDOW]
        if recent:
            summary += (
                f" A Form D was filed {recent[-1].source_date.isoformat()}; investors in that "
                "round may still be inside the six-month application window."
            )

    return ProgramMatch(
        program_id=PROGRAM_ID,
        program_name=PROGRAM_NAME,
        result=result,
        summary=summary,
        checks=tuple(checks),
        confirm_before_applying=_attested(v),
        sources=v.sources,
        as_of=as_of,
        rules_version=v.version,
    )


def _eligible_technology_check(criterion: Criterion, p: CompanyProfile) -> CheckResult:
    form_ds = p.form_d_records
    if form_ds:
        latest = form_ds[-1]
        group = latest.form_d.industry_group if latest.form_d else None
        if group in INELIGIBLE_INDUSTRY_GROUPS:
            return CheckResult(
                criterion,
                CheckOutcome.FAIL,
                f"Latest Form D industry group is {group}.",
                (latest.provenance,),
            )
        if group in ELIGIBLE_INDUSTRY_GROUPS:
            return CheckResult(
                criterion,
                CheckOutcome.PASS,
                f"Latest Form D industry group is {group}.",
                (latest.provenance,),
            )
    if p.sbir_records:
        return CheckResult(
            criterion,
            CheckOutcome.PASS,
            "Holds a federal SBIR/STTR R&D award; the specific eligible technology should be "
            "confirmed.",
            tuple(r.provenance for r in p.sbir_records),
            needs_confirmation=True,
        )
    group = form_ds[-1].form_d.industry_group if form_ds and form_ds[-1].form_d else None
    return CheckResult(
        criterion,
        CheckOutcome.UNKNOWN,
        f"Form D industry group ({group or 'not stated'}) does not settle whether the primary "
        "business is an eligible technology.",
        tuple(r.provenance for r in form_ds),
    )
