"""CSIT SBIR/STTR Direct Financial Assistance Grant (Round 5).

Criteria are from CSIT's Round 5 Notice of Funding Availability, effective
January 15, 2026. The program has two award types, checked separately:

* Direct Funding Grant ($25,000) for companies with an active federal
  Phase I, Fast Track, or Direct to Phase II award.
* Bridge Funding Grant ($50,000) for companies that finished a Phase I in the
  last two years and are waiting on a Phase II decision.

A company cannot use the same federal award for both.
"""

from __future__ import annotations

from datetime import date, timedelta

from gauge.core.models import CompanyProfile, NormalizedRecord, SbirPhase
from gauge.programs.base import (
    Basis,
    CheckOutcome,
    CheckResult,
    Criterion,
    MatchResult,
    ProgramMatch,
    ProgramSource,
    best_of,
    decide,
    default_summary,
)

PROGRAM_ID = "csit_sbir_support"
PROGRAM_NAME = "CSIT SBIR/STTR Direct Financial Assistance"
RULES_VERSION = "csit-round5-2026-01-15"
EFFECTIVE = date(2026, 1, 15)

NOFA = ProgramSource(
    title="CSIT Round 5 SBIR/STTR Direct Financial Assistance Grant NOFA",
    url="https://www.njeda.gov/wp-content/uploads/2026/01/CSIT_SBIR-Round-5-NOFA_2026.pdf",
    reviewed_on=date(2026, 9, 25),
    effective=EFFECTIVE,
)
PROGRAM_PAGE = ProgramSource(
    title="SBIR/STTR Direct Financial Assistance Program (Phase 5), NJEDA",
    url="https://www.njeda.gov/sbir-sttr-direct-financial-assistance-program-phase-5/",
    reviewed_on=date(2026, 9, 25),
)
SOURCES = (NOFA, PROGRAM_PAGE)

LIFETIME_PHASE_I_TYPE_CAP = 5
LIFETIME_PHASE_II_CAP = 4  # Bridge only
BRIDGE_LOOKBACK = timedelta(days=2 * 365)
# Awards with no end date in the record: treat as possibly active for this long.
UNDATED_AWARD_WINDOW = timedelta(days=2 * 365)

PHASE_I_TYPES = (SbirPhase.PHASE_I, SbirPhase.FAST_TRACK, SbirPhase.DIRECT_TO_PHASE_II)


def _c(id: str, text: str, basis: Basis, question: str) -> Criterion:
    return Criterion(id, text, basis, NOFA, question)


DIRECT_ACTIVE_AWARD = _c(
    "direct.active_award",
    "Has an active federal SBIR/STTR Phase I, Fast Track, or Direct to Phase II award.",
    Basis.SCREENED,
    "Is the company's federal Phase I, Fast Track, or Direct to Phase II award still active?",
)
DIRECT_NJ_PERFORMANCE = _c(
    "direct.nj_place_of_performance",
    "The award's primary place of performance is a New Jersey address.",
    Basis.SCREENED,
    "Is the primary place of performance on the federal award a New Jersey address?",
)
DIRECT_AWARD_CAP = _c(
    "direct.lifetime_award_cap",
    "No more than five lifetime federal Phase I, Fast Track, or Direct to Phase II awards.",
    Basis.SCREENED,
    "How many federal Phase I, Fast Track, and Direct to Phase II awards has the company won?",
)
BRIDGE_RECENT_PHASE_I = _c(
    "bridge.recent_completed_phase_i",
    "Completed a federal Phase I award with a New Jersey place of performance, "
    "awarded no earlier than two years before applying.",
    Basis.SCREENED,
    "Has the company completed its Phase I award, and was the final report accepted?",
)
BRIDGE_NJ_PERFORMANCE = _c(
    "bridge.nj_place_of_performance",
    "The Phase I award's place of performance is a New Jersey address.",
    Basis.SCREENED,
    "Is the primary place of performance on the Phase I award a New Jersey address?",
)
BRIDGE_PHASE_II_PENDING = _c(
    "bridge.phase_ii_pending",
    "Has submitted a federal Phase II application that has not yet been decided.",
    Basis.SCREENED,
    "Has the company submitted a Phase II proposal that is still awaiting a federal decision?",
)
BRIDGE_AWARD_CAPS = _c(
    "bridge.lifetime_award_caps",
    "No more than five lifetime Phase I-type awards and four lifetime Phase II awards.",
    Basis.SCREENED,
    "How many federal Phase I-type and Phase II awards has the company won?",
)

ATTESTED = (
    _c(
        "good_standing_nj",
        "Authorized and in good standing to conduct business in New Jersey.",
        Basis.ATTESTED,
        "Is the company authorized and in good standing to do business in New Jersey?",
    ),
    _c(
        "tax_clearance",
        "Holds a current New Jersey Tax Clearance Certificate listing CSIT.",
        Basis.ATTESTED,
        "Does the company have a current NJ Tax Clearance Certificate that lists CSIT?",
    ),
    _c(
        "dol_dep_standing",
        "In good standing with the NJ Department of Labor and Department of "
        "Environmental Protection.",
        Basis.ATTESTED,
        "Is the company in good standing with NJ DOL and DEP?",
    ),
    _c(
        "one_full_time_worker",
        "At least one full-time worker (35 hours/week; founders and contractors count, "
        "paid or unpaid).",
        Basis.ATTESTED,
        "Does the company have at least one full-time worker?",
    ),
    _c(
        "half_hours_in_nj",
        "At least 50% of all worker, founder, and contractor hours are worked in New Jersey.",
        Basis.ATTESTED,
        "Are at least half of the company's total work hours performed in New Jersey?",
    ),
    _c(
        "not_cannabis",
        "Not a cannabis licensee or otherwise barred under N.J.S.A. 24:6I-49.",
        Basis.ATTESTED,
        "Is the company free of cannabis-license restrictions on state incentives?",
    ),
)
BRIDGE_ATTESTED = (
    *ATTESTED,
    _c(
        "phase_i_final_report_accepted",
        "The Phase I final report was accepted by the federal agency.",
        Basis.ATTESTED,
        "Has the federal agency accepted the Phase I final report?",
    ),
)


def _award_start(rec: NormalizedRecord) -> date:
    assert rec.sbir is not None
    return rec.sbir.award_start or rec.source_date


def _nj_performance(criterion: Criterion, awards: list[NormalizedRecord]) -> CheckResult:
    evidence = tuple(r.provenance for r in awards)
    stated = [
        r.sbir.place_of_performance_state.upper()
        for r in awards
        if r.sbir and r.sbir.place_of_performance_state
    ]
    if stated:
        if "NJ" in stated:
            return CheckResult(
                criterion,
                CheckOutcome.PASS,
                "Award record lists NJ as place of performance.",
                evidence,
            )
        return CheckResult(
            criterion,
            CheckOutcome.FAIL,
            "Award record lists a place of performance outside NJ.",
            evidence,
        )
    if any(r.address is not None and r.address.in_new_jersey for r in awards):
        return CheckResult(
            criterion,
            CheckOutcome.PASS,
            "The award record has no place of performance, so the awardee's NJ address is "
            "used in its place.",
            evidence,
            needs_confirmation=True,
        )
    return CheckResult(
        criterion,
        CheckOutcome.UNKNOWN,
        "The award record shows neither a place of performance nor an NJ awardee address.",
        evidence,
    )


def _phase_i_type_count(awards: list[NormalizedRecord]) -> int:
    return sum(1 for r in awards if r.sbir and r.sbir.phase in PHASE_I_TYPES)


def _phase_ii_count(awards: list[NormalizedRecord]) -> int:
    return sum(
        1
        for r in awards
        if r.sbir and r.sbir.phase in (SbirPhase.PHASE_II, SbirPhase.DIRECT_TO_PHASE_II)
    )


def _evaluate_direct(profile: CompanyProfile, as_of: date) -> ProgramMatch:
    awards = profile.as_of(as_of).sbir_records
    phase_i_type = [r for r in awards if r.sbir and r.sbir.phase in PHASE_I_TYPES]
    active = [
        r
        for r in phase_i_type
        if r.sbir and r.sbir.award_end is not None and _award_start(r) <= as_of <= r.sbir.award_end
    ]
    undated_recent = [
        r
        for r in phase_i_type
        if r.sbir and r.sbir.award_end is None and as_of - _award_start(r) <= UNDATED_AWARD_WINDOW
    ]

    checks: list[CheckResult] = []
    if active:
        ends = ", ".join(str(r.sbir.award_end) for r in active if r.sbir)
        checks.append(
            CheckResult(
                DIRECT_ACTIVE_AWARD,
                CheckOutcome.PASS,
                f"Active award(s) with end date(s) {ends}.",
                tuple(r.provenance for r in active),
            )
        )
        checks.append(_nj_performance(DIRECT_NJ_PERFORMANCE, active))
    elif undated_recent:
        checks.append(
            CheckResult(
                DIRECT_ACTIVE_AWARD,
                CheckOutcome.UNKNOWN,
                "A recent award has no end date in the record.",
                tuple(r.provenance for r in undated_recent),
            )
        )
        checks.append(_nj_performance(DIRECT_NJ_PERFORMANCE, undated_recent))
    else:
        checks.append(
            CheckResult(
                DIRECT_ACTIVE_AWARD,
                CheckOutcome.FAIL,
                "No active Phase I, Fast Track, or Direct to Phase II award in SBIR/STTR records"
                f" as of {as_of.isoformat()}.",
                tuple(r.provenance for r in phase_i_type),
            )
        )

    n = _phase_i_type_count(awards)
    checks.append(
        CheckResult(
            DIRECT_AWARD_CAP,
            CheckOutcome.PASS if n <= LIFETIME_PHASE_I_TYPE_CAP else CheckOutcome.FAIL,
            f"{n} Phase I-type award(s) in linked SBIR/STTR records "
            f"(cap {LIFETIME_PHASE_I_TYPE_CAP}).",
            tuple(r.provenance for r in phase_i_type),
        )
    )
    result = decide(checks)
    return ProgramMatch(
        program_id=f"{PROGRAM_ID}.direct",
        program_name="CSIT Direct Funding Grant ($25,000)",
        result=result,
        summary=default_summary(result, checks),
        checks=tuple(checks),
        confirm_before_applying=ATTESTED,
        sources=SOURCES,
        as_of=as_of,
        rules_version=RULES_VERSION,
    )


def _evaluate_bridge(profile: CompanyProfile, as_of: date) -> ProgramMatch:
    awards = profile.as_of(as_of).sbir_records
    phase_i = [r for r in awards if r.sbir and r.sbir.phase is SbirPhase.PHASE_I]
    recent = [r for r in phase_i if as_of - _award_start(r) <= BRIDGE_LOOKBACK]
    completed = [r for r in recent if r.sbir and r.sbir.award_end and r.sbir.award_end <= as_of]
    undated = [r for r in recent if r.sbir and r.sbir.award_end is None]

    checks: list[CheckResult] = []
    if completed:
        checks.append(
            CheckResult(
                BRIDGE_RECENT_PHASE_I,
                CheckOutcome.PASS,
                "Phase I award from the last two years has ended.",
                tuple(r.provenance for r in completed),
                needs_confirmation=True,  # completion and report acceptance are not in the record
            )
        )
        checks.append(_nj_performance(BRIDGE_NJ_PERFORMANCE, completed))
    elif undated:
        checks.append(
            CheckResult(
                BRIDGE_RECENT_PHASE_I,
                CheckOutcome.UNKNOWN,
                "A Phase I award from the last two years has no end date in the record.",
                tuple(r.provenance for r in undated),
            )
        )
        checks.append(_nj_performance(BRIDGE_NJ_PERFORMANCE, undated))
    elif recent:
        checks.append(
            CheckResult(
                BRIDGE_RECENT_PHASE_I,
                CheckOutcome.FAIL,
                "The Phase I award from the last two years is still active, so it has not been "
                "completed.",
                tuple(r.provenance for r in recent),
            )
        )
    else:
        checks.append(
            CheckResult(
                BRIDGE_RECENT_PHASE_I,
                CheckOutcome.FAIL,
                "No Phase I award in the two years before "
                f"{as_of.isoformat()} in SBIR/STTR records.",
                tuple(r.provenance for r in phase_i),
            )
        )

    checks.append(
        CheckResult(
            BRIDGE_PHASE_II_PENDING,
            CheckOutcome.UNKNOWN,
            "Pending Phase II proposals are not public.",
        )
    )
    n_i, n_ii = _phase_i_type_count(awards), _phase_ii_count(awards)
    within = n_i <= LIFETIME_PHASE_I_TYPE_CAP and n_ii <= LIFETIME_PHASE_II_CAP
    checks.append(
        CheckResult(
            BRIDGE_AWARD_CAPS,
            CheckOutcome.PASS if within else CheckOutcome.FAIL,
            f"{n_i} Phase I-type and {n_ii} Phase II award(s) in linked SBIR/STTR records "
            f"(caps {LIFETIME_PHASE_I_TYPE_CAP} and {LIFETIME_PHASE_II_CAP}).",
            tuple(r.provenance for r in awards),
        )
    )
    result = decide(checks)
    return ProgramMatch(
        program_id=f"{PROGRAM_ID}.bridge",
        program_name="CSIT Bridge Funding Grant ($50,000)",
        result=result,
        summary=default_summary(result, checks),
        checks=tuple(checks),
        confirm_before_applying=BRIDGE_ATTESTED,
        sources=SOURCES,
        as_of=as_of,
        rules_version=RULES_VERSION,
    )


def evaluate(profile: CompanyProfile, as_of: date) -> ProgramMatch:
    """Check a company against both CSIT award types and report the better fit."""
    if as_of < EFFECTIVE:
        raise ValueError(
            f"{RULES_VERSION} applies from {EFFECTIVE}; earlier CSIT rounds are not encoded."
        )
    direct = _evaluate_direct(profile, as_of)
    bridge = _evaluate_bridge(profile, as_of)
    best = best_of([direct, bridge])
    if best.result is MatchResult.NOT_A_MATCH:
        summary = "Neither award type fits: " + " / ".join(
            f"{m.program_name}: {m.summary}" for m in (direct, bridge)
        )
    else:
        summary = f"Best fit is the {best.program_name}. {best.summary}"
    return ProgramMatch(
        program_id=PROGRAM_ID,
        program_name=PROGRAM_NAME,
        result=best.result,
        summary=summary,
        checks=best.checks,
        confirm_before_applying=best.confirm_before_applying,
        sources=SOURCES,
        as_of=as_of,
        rules_version=RULES_VERSION,
        components=(direct, bridge),
    )
