from datetime import date

from gauge.core.models import Address
from gauge.programs import life_sciences_fund as lshf
from gauge.programs.base import CheckOutcome, MatchResult
from tests.factories import form_d, profile, sbir

AS_OF = date(2026, 9, 1)
NY = Address(city="New York", state="NY")


def check(match, criterion_id):
    return next(c for c in match.checks if c.criterion.id == criterion_id)


def biotech(**facts):
    defaults = {"industry_group": "Biotechnology", "filed": date(2026, 4, 1)}
    defaults.update(facts)
    return form_d("Pinewood Therapeutics, Inc.", **defaults)


def test_clear_match_nj_biotech_raising_small_round():
    p = profile(biotech(total_offering_amount=6_000_000.0), sbir(agency="HHS", employee_count=14))
    m = lshf.evaluate(p, AS_OF)
    assert m.result is MatchResult.STRONG_MATCH
    assert "Tech Council Ventures" in m.summary
    assert check(m, "active_round_under_20m").outcome is CheckOutcome.PASS
    # A filing address is not proof of HQ, so it is still flagged to confirm.
    assert any("headquartered in NJ" in q for q in m.verification_questions)


def test_clear_non_match_round_too_large():
    p = profile(biotech(total_offering_amount=35_000_000.0), sbir(agency="HHS", employee_count=14))
    m = lshf.evaluate(p, AS_OF)
    assert m.result is MatchResult.NOT_A_MATCH
    assert check(m, "active_round_under_20m").outcome is CheckOutcome.FAIL


def test_clear_non_match_not_health_sector():
    m = lshf.evaluate(profile(form_d(industry_group="Commercial Banking")), AS_OF)
    assert m.result is MatchResult.NOT_A_MATCH
    assert check(m, "life_science_focus").outcome is CheckOutcome.FAIL


def test_clear_non_match_too_many_employees():
    m = lshf.evaluate(profile(biotech(), sbir(agency="HHS", employee_count=900)), AS_OF)
    assert check(m, "headcount").outcome is CheckOutcome.FAIL
    assert m.result is MatchResult.NOT_A_MATCH


def test_missing_info_no_recent_raise_and_no_headcount():
    m = lshf.evaluate(profile(biotech(filed=date(2024, 1, 1))), AS_OF)
    assert m.result is MatchResult.POTENTIAL_MATCH
    assert check(m, "active_round_under_20m").outcome is CheckOutcome.UNKNOWN
    assert check(m, "headcount").outcome is CheckOutcome.UNKNOWN
    assert any("round size" in q for q in m.verification_questions)
    assert any("employees" in q for q in m.verification_questions)


def test_indefinite_offering_is_unknown():
    m = lshf.evaluate(profile(biotech(total_offering_amount=None)), AS_OF)
    assert check(m, "active_round_under_20m").outcome is CheckOutcome.UNKNOWN


def test_health_focus_from_sbir_topic_when_form_d_is_generic():
    p = profile(
        form_d(industry_group="Other Technology", filed=date(2026, 4, 1)),
        sbir(agency="NSF", topic_title="Point-of-care diagnostic assay", employee_count=5),
    )
    focus = check(lshf.evaluate(p, AS_OF), "life_science_focus")
    assert focus.outcome is CheckOutcome.PASS and focus.needs_confirmation


def test_non_health_tech_is_unknown_not_failed():
    p = profile(form_d(industry_group="Other Technology", filed=date(2026, 4, 1)))
    focus = check(lshf.evaluate(p, AS_OF), "life_science_focus")
    assert focus.outcome is CheckOutcome.UNKNOWN


def test_out_of_state_address_is_unknown_because_employee_route_exists():
    m = lshf.evaluate(profile(biotech(address=NY)), AS_OF)
    assert check(m, "nj_location").outcome is CheckOutcome.UNKNOWN


def test_explanation_and_evidence_cite_both_sources():
    m = lshf.evaluate(profile(biotech()), AS_OF)
    text = "\n".join(m.explain())
    assert lshf.PROGRAM_PAGE.url in text and lshf.SSBCI_NOTICE.url in text
    assert lshf.PROGRAM_PAGE.url in m.evidence_items()[0].limitations
