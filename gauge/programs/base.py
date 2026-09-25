"""Shared machinery for New Jersey program matching rules.

A rule is a list of criteria taken from the program's official documents.
Each criterion is one of two kinds:

* ``SCREENED``: public records can answer it. It is checked and comes out
  PASS, FAIL, or UNKNOWN, with the records that decided it.
* ``ATTESTED``: only the company can establish it (tax clearance, payroll
  location, good standing). It never changes the result; it is listed as
  something to confirm before applying.

The result follows from the screened checks alone:

* any FAIL gives NOT_A_MATCH
* otherwise any UNKNOWN gives POTENTIAL_MATCH, with a verification question
  for each unknown
* otherwise STRONG_MATCH

A strong match means the public records are consistent with every criterion
we can screen. It is not an eligibility determination; the program decides
that at application.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from gauge.core.models import EvidenceItem, EvidenceKind, Provenance


class MatchResult(StrEnum):
    STRONG_MATCH = "strong_match"
    POTENTIAL_MATCH = "potential_match_verify"
    NOT_A_MATCH = "not_a_match"


_RESULT_RANK = {
    MatchResult.STRONG_MATCH: 2,
    MatchResult.POTENTIAL_MATCH: 1,
    MatchResult.NOT_A_MATCH: 0,
}

RESULT_LABELS = {
    MatchResult.STRONG_MATCH: "Strong match",
    MatchResult.POTENTIAL_MATCH: "Potential match (verify)",
    MatchResult.NOT_A_MATCH: "Not a match",
}


class CheckOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class Basis(StrEnum):
    SCREENED = "screened"
    ATTESTED = "attested"


@dataclass(frozen=True)
class ProgramSource:
    """An official document a rule's criteria were taken from."""

    title: str
    url: str
    reviewed_on: date
    effective: date | None = None  # the document's own effective or publication date
    note: str = ""

    def cite(self) -> str:
        return f"{self.title} ({self.url}), reviewed {self.reviewed_on.isoformat()}"


@dataclass(frozen=True)
class Criterion:
    id: str
    text: str
    basis: Basis
    source: ProgramSource
    verification_question: str


@dataclass(frozen=True)
class CheckResult:
    criterion: Criterion
    outcome: CheckOutcome
    explanation: str
    evidence: tuple[Provenance, ...] = ()
    # True when the check passed on a proxy (for example, the awardee address
    # standing in for place of performance) that the company should confirm.
    needs_confirmation: bool = False


@dataclass(frozen=True)
class ProgramMatch:
    program_id: str
    program_name: str
    result: MatchResult
    summary: str
    checks: tuple[CheckResult, ...]
    confirm_before_applying: tuple[Criterion, ...]
    sources: tuple[ProgramSource, ...]
    as_of: date
    rules_version: str
    # Programs with separate award types (for example CSIT's Direct and Bridge
    # grants) report each one here; the top-level result is the best of them.
    components: tuple[ProgramMatch, ...] = field(default=())

    @property
    def verification_questions(self) -> tuple[str, ...]:
        questions = [
            c.criterion.verification_question
            for c in self.checks
            if c.outcome is CheckOutcome.UNKNOWN or c.needs_confirmation
        ]
        return tuple(dict.fromkeys(questions))

    def explain(self) -> list[str]:
        """The result line by line, each line naming its evidence."""
        lines = [f"{self.program_name}: {RESULT_LABELS[self.result]}. {self.summary}"]
        for c in self.checks:
            cited = ", ".join(p.source_url for p in c.evidence) or "no public record"
            lines.append(
                f"[{c.outcome.value.upper()}] {c.criterion.text} {c.explanation} "
                f"(evidence: {cited})"
            )
        for crit in self.confirm_before_applying:
            lines.append(f"[CONFIRM] {crit.text}")
        lines.extend(f"Criteria source: {s.cite()}" for s in self.sources)
        return lines

    def evidence_items(self) -> list[EvidenceItem]:
        """Evidence-card entries: the inferred result plus one gap per open question."""
        items = [
            EvidenceItem(
                claim=f"{self.program_name}: {RESULT_LABELS[self.result]}",
                kind=EvidenceKind.INFERRED,
                value=self.result.value,
                limitations=(
                    "Screened against public records only; the program decides eligibility "
                    "at application. Criteria: " + "; ".join(s.cite() for s in self.sources)
                ),
            )
        ]
        items.extend(
            EvidenceItem(claim=q, kind=EvidenceKind.UNKNOWN) for q in self.verification_questions
        )
        return items


def decide(checks: Iterable[CheckResult]) -> MatchResult:
    outcomes = {c.outcome for c in checks}
    if CheckOutcome.FAIL in outcomes:
        return MatchResult.NOT_A_MATCH
    if CheckOutcome.UNKNOWN in outcomes:
        return MatchResult.POTENTIAL_MATCH
    return MatchResult.STRONG_MATCH


def best_of(matches: Sequence[ProgramMatch]) -> ProgramMatch:
    """The component with the best result; earlier components win ties."""
    return max(matches, key=lambda m: _RESULT_RANK[m.result])


def default_summary(result: MatchResult, checks: Sequence[CheckResult]) -> str:
    if result is MatchResult.NOT_A_MATCH:
        failed = [c.criterion.text for c in checks if c.outcome is CheckOutcome.FAIL]
        return "Public records conflict with: " + "; ".join(failed)
    if result is MatchResult.POTENTIAL_MATCH:
        n = sum(c.outcome is CheckOutcome.UNKNOWN for c in checks)
        return f"No conflicts in public records; {n} screenable criteria need verification."
    return "Public records are consistent with every screenable criterion."
