from datetime import date

import pytest

from gauge.core.models import Address, EvidenceKind, SbirPhase
from gauge.programs import csit_sbir
from gauge.programs.base import CheckOutcome, MatchResult
from tests.factories import form_d, profile, sbir

AS_OF = date(2026, 9, 1)
OHIO = Address(city="Columbus", state="OH")


def check(match, criterion_id):
    return next(c for c in match.checks if c.criterion.id == criterion_id)


def test_clear_match_active_phase_i_with_nj_place_of_performance():
    p = profile(
        sbir(
            awarded=date(2026, 3, 1),
            award_end=date(2027, 2, 28),
            place_of_performance_state="NJ",
        )
    )
    m = csit_sbir.evaluate(p, AS_OF)
    assert m.result is MatchResult.STRONG_MATCH
    assert m.components[0].result is MatchResult.STRONG_MATCH  # Direct
    assert "Direct Funding Grant" in m.summary
    assert m.verification_questions == ()
    assert len(m.confirm_before_applying) == len(csit_sbir.ATTESTED)


def test_clear_non_match_no_sbir_history():
    m = csit_sbir.evaluate(profile(form_d()), AS_OF)
    assert m.result is MatchResult.NOT_A_MATCH
    assert all(c.result is MatchResult.NOT_A_MATCH for c in m.components)
    assert m.summary.startswith("Neither award type fits")


def test_missing_info_undated_award_is_potential_with_question():
    p = profile(sbir(awarded=date(2026, 2, 1), award_end=None))
    m = csit_sbir.evaluate(p, AS_OF)
    assert m.result is MatchResult.POTENTIAL_MATCH
    assert check(m, "direct.active_award").outcome is CheckOutcome.UNKNOWN
    assert any("still active" in q for q in m.verification_questions)


def test_awardee_address_stands_in_for_place_of_performance_but_asks_to_confirm():
    p = profile(sbir(awarded=date(2026, 3, 1), award_end=date(2027, 2, 28)))
    m = csit_sbir.evaluate(p, AS_OF)
    nj = check(m, "direct.nj_place_of_performance")
    assert nj.outcome is CheckOutcome.PASS
    assert nj.needs_confirmation
    assert m.result is MatchResult.STRONG_MATCH
    assert any("place of performance" in q for q in m.verification_questions)


def test_out_of_state_place_of_performance_fails():
    p = profile(
        sbir(
            awarded=date(2026, 3, 1),
            award_end=date(2027, 2, 28),
            place_of_performance_state="OH",
            address=OHIO,
        )
    )
    direct = csit_sbir.evaluate(p, AS_OF).components[0]
    assert direct.result is MatchResult.NOT_A_MATCH
    assert check(direct, "direct.nj_place_of_performance").outcome is CheckOutcome.FAIL


def test_more_than_five_phase_i_awards_fails_direct():
    old = [
        sbir(awarded=date(2019 + i % 5, 1, 1), award_end=date(2020 + i % 5, 1, 1)) for i in range(5)
    ]
    active = sbir(awarded=date(2026, 3, 1), award_end=date(2027, 2, 28))
    direct = csit_sbir.evaluate(profile(*old, active), AS_OF).components[0]
    assert direct.result is MatchResult.NOT_A_MATCH
    assert check(direct, "direct.lifetime_award_cap").outcome is CheckOutcome.FAIL


def test_bridge_is_at_most_potential_because_phase_ii_applications_are_private():
    p = profile(sbir(awarded=date(2025, 1, 15), award_end=date(2025, 12, 31)))
    m = csit_sbir.evaluate(p, AS_OF)
    bridge = m.components[1]
    assert bridge.result is MatchResult.POTENTIAL_MATCH
    assert m.result is MatchResult.POTENTIAL_MATCH
    assert "Bridge" in m.summary
    assert any("Phase II proposal" in q for q in m.verification_questions)


def test_bridge_fails_when_phase_i_is_still_running_or_too_old():
    running = profile(sbir(awarded=date(2026, 3, 1), award_end=date(2027, 2, 28)))
    assert csit_sbir.evaluate(running, AS_OF).components[1].result is MatchResult.NOT_A_MATCH
    stale = profile(sbir(awarded=date(2022, 1, 1), award_end=date(2022, 12, 31)))
    assert csit_sbir.evaluate(stale, AS_OF).components[1].result is MatchResult.NOT_A_MATCH


def test_bridge_phase_ii_cap():
    phase_ii = [
        sbir(awarded=date(2018 + i, 1, 1), phase=SbirPhase.PHASE_II, award_end=date(2019 + i, 1, 1))
        for i in range(5)
    ]
    recent = sbir(awarded=date(2025, 1, 15), award_end=date(2025, 12, 31))
    bridge = csit_sbir.evaluate(profile(*phase_ii, recent), AS_OF).components[1]
    assert check(bridge, "bridge.lifetime_award_caps").outcome is CheckOutcome.FAIL


def test_explanation_is_line_by_line_with_record_and_criteria_sources():
    award = sbir(awarded=date(2026, 3, 1), award_end=date(2027, 2, 28))
    m = csit_sbir.evaluate(profile(award), AS_OF)
    lines = m.explain()
    assert lines[0].startswith("CSIT SBIR/STTR Direct Financial Assistance: Strong match")
    assert any(award.provenance.source_url in line for line in lines)
    assert any(csit_sbir.NOFA.url in line for line in lines)
    assert sum(line.startswith("[CONFIRM]") for line in lines) == len(csit_sbir.ATTESTED)


def test_evidence_items_separate_inferred_result_from_open_questions():
    p = profile(sbir(awarded=date(2026, 2, 1), award_end=None))
    items = csit_sbir.evaluate(p, AS_OF).evidence_items()
    assert items[0].kind is EvidenceKind.INFERRED
    assert csit_sbir.NOFA.url in items[0].limitations
    assert {i.kind for i in items[1:]} == {EvidenceKind.UNKNOWN}


def test_rules_refuse_dates_before_round_5():
    with pytest.raises(ValueError, match="earlier CSIT rounds"):
        csit_sbir.evaluate(profile(sbir()), date(2025, 6, 1))
