from datetime import date

import pytest

from gauge.core.models import Address
from gauge.programs import angel_tax_credit as angel
from gauge.programs.base import CheckOutcome, MatchResult
from tests.factories import form_d, profile, sbir

AS_OF = date(2026, 9, 1)
PA = Address(city="Philadelphia", state="PA")


def check(match, criterion_id):
    return next(c for c in match.checks if c.criterion.id == criterion_id)


def test_clear_match_small_nj_tech_company():
    p = profile(form_d(filed=date(2026, 5, 1)), sbir(awarded=date(2026, 1, 10), employee_count=12))
    m = angel.evaluate(p, AS_OF)
    assert m.result is MatchResult.STRONG_MATCH
    assert m.rules_version == "angel-2026-01-01"
    assert "35% refundable credit" in m.summary
    assert "six-month application window" in m.summary
    assert m.verification_questions == ()


def test_clear_non_match_headcount_over_2026_cap():
    p = profile(form_d(), sbir(awarded=date(2026, 1, 10), employee_count=180))
    m = angel.evaluate(p, AS_OF)
    assert m.result is MatchResult.NOT_A_MATCH
    assert check(m, "headcount").outcome is CheckOutcome.FAIL
    assert "fewer than 150" in check(m, "headcount").criterion.text


def test_same_headcount_passed_under_pre_2026_rules():
    p = profile(form_d(filed=date(2022, 6, 1)), sbir(awarded=date(2022, 3, 1), employee_count=180))
    m = angel.evaluate(p, date(2022, 12, 31))
    assert m.rules_version == "angel-pre-2026"
    assert check(m, "headcount").outcome is CheckOutcome.PASS
    assert "20% refundable credit" in m.summary
    assert angel.PRIOR_PAGE in m.sources


def test_clear_non_match_ineligible_industry():
    m = angel.evaluate(profile(form_d(industry_group="Restaurants")), AS_OF)
    assert m.result is MatchResult.NOT_A_MATCH
    assert check(m, "eligible_technology").outcome is CheckOutcome.FAIL


def test_missing_info_form_d_only_is_potential_with_questions():
    m = angel.evaluate(profile(form_d(industry_group="Business Services")), AS_OF)
    assert m.result is MatchResult.POTENTIAL_MATCH
    assert check(m, "headcount").outcome is CheckOutcome.UNKNOWN
    assert check(m, "eligible_technology").outcome is CheckOutcome.UNKNOWN
    questions = m.verification_questions
    assert any("full-time employees" in q for q in questions)
    assert any("eligible technology" in q for q in questions)


def test_out_of_state_only_is_potential_not_rejected():
    p = profile(form_d(address=PA), sbir(address=PA, employee_count=5))
    m = angel.evaluate(p, AS_OF)
    assert check(m, "nj_presence").outcome is CheckOutcome.UNKNOWN
    assert m.result is MatchResult.POTENTIAL_MATCH


def test_sbir_award_passes_technology_but_asks_which_one():
    m = angel.evaluate(profile(sbir(awarded=date(2026, 1, 10), employee_count=4)), AS_OF)
    tech = check(m, "eligible_technology")
    assert tech.outcome is CheckOutcome.PASS and tech.needs_confirmation
    assert any("eligible technology" in q for q in m.verification_questions)


def test_attested_items_cover_workforce_and_investment_terms():
    m = angel.evaluate(profile(form_d()), AS_OF)
    ids = {c.id for c in m.confirm_before_applying}
    assert {"nj_workforce_75", "qualified_investment", "application_window"} <= ids


def test_explanation_cites_program_source():
    lines = angel.evaluate(profile(form_d()), AS_OF).explain()
    assert any(angel.PROGRAM_PAGE.url in line for line in lines)


@pytest.mark.parametrize(
    ("as_of", "version"),
    [
        (date(2025, 12, 31), "angel-pre-2026"),
        (date(2026, 1, 1), "angel-2026-01-01"),
        (date(2019, 1, 1), "angel-pre-2026"),
    ],
)
def test_rule_version_boundaries(as_of, version):
    assert angel.rule_version(as_of).version == version
