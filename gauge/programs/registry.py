"""Every encoded New Jersey program rule, in display order."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from gauge.core.models import CompanyProfile
from gauge.programs import angel_tax_credit, csit_sbir, life_sciences_fund
from gauge.programs.base import ProgramMatch

Evaluator = Callable[[CompanyProfile, date], ProgramMatch]

PROGRAMS: dict[str, Evaluator] = {
    csit_sbir.PROGRAM_ID: csit_sbir.evaluate,
    angel_tax_credit.PROGRAM_ID: angel_tax_credit.evaluate,
    life_sciences_fund.PROGRAM_ID: life_sciences_fund.evaluate,
}


def evaluate_all(profile: CompanyProfile, as_of: date) -> dict[str, ProgramMatch]:
    return {pid: evaluate(profile, as_of) for pid, evaluate in PROGRAMS.items()}
