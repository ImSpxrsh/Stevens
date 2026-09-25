"""Regression tests for the highest-risk Gauge logic.

Each test pins a rule that should only change deliberately. If one fails,
the change it caught is a product decision, not a refactor: update the test
in the same PR and say why.
"""

from __future__ import annotations

import itertools
from datetime import date

import pytest

from gauge.classifier import PRIOR_MODEL, ExclusionReason, StartupLabel, classify
from gauge.classifier.features import FEATURE_NAMES, extract_features
from gauge.core.models import Address, SbirPhase
from gauge.pipeline import run
from gauge.programs import angel_tax_credit, csit_sbir, life_sciences_fund
from gauge.programs.base import MatchResult
from gauge.review import (
    Action,
    ActorType,
    AlertGate,
    LinkBasis,
    ReviewStatus,
    ReviewStore,
    alert_gate,
    link_records,
)
from gauge.review.linking import LinkResult, RecordLink
from gauge.review.models import ReviewItem, ReviewKind, now
from tests.factories import form_d, profile, sbir

AS_OF = date(2026, 9, 1)
NEWARK = Address(city="Newark", state="NJ", postal_code="07102")

# --- Startup exclusion rules ------------------------------------------------

EXCLUDED_RECORDS = {
    ExclusionReason.FUND: form_d(
        "Beacon Seed Fund III, L.P.", industry_group="Pooled Investment Fund"
    ),
    ExclusionReason.REAL_ESTATE: form_d("Harborview Residences LLC", industry_group="Residential"),
    ExclusionReason.ESTABLISHED: form_d(
        "Old Line Manufacturing", revenue_range="Over $100,000,000"
    ),
    ExclusionReason.PUBLIC_COMPANY: form_d("Listed Co", cik="0000999999"),
}


@pytest.mark.parametrize("reason", list(EXCLUDED_RECORDS))
def test_excluded_companies_never_reach_discovery_programs_or_alerts(reason):
    record = EXCLUDED_RECORDS[reason]
    out = run([record], AS_OF, ReviewStore(), public_ciks={"0000999999"})
    (company_id,) = out.profiles
    c = out.classifications[company_id]
    assert c.exclusion is not None and c.exclusion.reason is reason
    assert c.label is StartupLabel.NOT_STARTUP
    assert c not in out.discovery.ranked and c not in out.discovery.uncertain
    assert company_id not in out.program_matches


# --- Logistic-regression features and scoring --------------------------------


def test_features_are_binary_and_complete():
    p = profile(form_d(revenue_range="No Revenues"), sbir(employee_count=4))
    values = extract_features(p, AS_OF).values
    assert set(values) == set(FEATURE_NAMES)
    assert set(values.values()) <= {0.0, 1.0}


@pytest.mark.parametrize(
    ("feature", "sign"),
    [
        ("incorporated_within_5y", +1),
        ("sbir_phase_i", +1),
        ("no_revenue", +1),
        ("incorporated_over_5y", -1),
        ("revenue_over_1m", -1),
        ("large_team", -1),
    ],
)
def test_prior_weight_directions_are_pinned(feature, sign):
    assert PRIOR_MODEL.weights[feature] * sign > 0


@pytest.mark.parametrize("feature", [n for n in FEATURE_NAMES if PRIOR_MODEL.weights[n] > 0])
def test_positive_evidence_never_lowers_probability(feature):
    base = dict.fromkeys(FEATURE_NAMES, 0.0)
    with_feature = {**base, feature: 1.0}
    assert PRIOR_MODEL.predict_proba(with_feature) > PRIOR_MODEL.predict_proba(base)


def test_reference_score_is_stable():
    p = profile(form_d(revenue_range="No Revenues", filed=date(2026, 5, 1)))
    assert classify(p, AS_OF).probability == pytest.approx(0.9781, abs=1e-4)


# --- Matching: exact SEC ID, fuzzy routing, rejected merges -------------------


def test_exact_sec_id_always_merges_even_with_different_names():
    a = form_d("Acme Robotics, Inc.", cik="0001")
    b = form_d("Totally Renamed Corp", cik="0001")
    result = link_records([a, b], ReviewStore())
    assert result.links[b.key].basis is LinkBasis.EXACT_CIK
    assert result.links[a.key].company_id == result.links[b.key].company_id


def test_fuzzy_match_routes_to_review_and_does_not_merge():
    filing = form_d("Acme Robotics, Inc.", cik="0001")
    award = sbir("Acme Robotics", address=NEWARK)
    store = ReviewStore()
    result = link_records([filing, award], store)
    assert result.links[award.key].company_id != "cik:0001"
    assert [i.status for i in store.items()] == [ReviewStatus.OPEN]


def test_rejected_merge_stays_rejected_across_reruns():
    filing = form_d("Acme Robotics, Inc.", cik="0001")
    award = sbir("Acme Robotics", address=NEWARK)
    store = ReviewStore()
    link_records([filing, award], store)
    (item,) = store.items()
    store.decide(item.item_id, Action.REJECT_MERGE, "Priya")
    for _ in range(3):
        result = link_records([filing, award], store)
        assert result.links[award.key].company_id != "cik:0001"
    assert len(store.items()) == 1


# --- Program rules: every result type for every program ----------------------

PROGRAM_CASES = {
    csit_sbir: {
        MatchResult.STRONG_MATCH: profile(
            sbir(
                awarded=date(2026, 3, 1),
                award_end=date(2027, 2, 28),
                place_of_performance_state="NJ",
            )
        ),
        MatchResult.POTENTIAL_MATCH: profile(sbir(awarded=date(2026, 3, 1), award_end=None)),
        MatchResult.NOT_A_MATCH: profile(form_d()),
    },
    angel_tax_credit: {
        MatchResult.STRONG_MATCH: profile(
            form_d(), sbir(awarded=date(2026, 1, 1), employee_count=10)
        ),
        MatchResult.POTENTIAL_MATCH: profile(form_d(industry_group="Business Services")),
        MatchResult.NOT_A_MATCH: profile(form_d(industry_group="Restaurants")),
    },
    life_sciences_fund: {
        MatchResult.STRONG_MATCH: profile(
            form_d(industry_group="Biotechnology", filed=date(2026, 5, 1)),
            sbir(agency="HHS", employee_count=10),
        ),
        MatchResult.POTENTIAL_MATCH: profile(
            form_d(industry_group="Biotechnology", filed=date(2024, 1, 1))
        ),
        MatchResult.NOT_A_MATCH: profile(form_d(industry_group="Commercial Banking")),
    },
}


@pytest.mark.parametrize(
    ("program", "expected"),
    [(prog, result) for prog, cases in PROGRAM_CASES.items() for result in cases],
    ids=lambda x: getattr(x, "PROGRAM_ID", getattr(x, "value", str(x))),
)
def test_each_program_returns_each_result_type(program, expected):
    match = program.evaluate(PROGRAM_CASES[program][expected], AS_OF)
    assert match.result is expected
    if expected is MatchResult.POTENTIAL_MATCH:
        assert match.verification_questions, "potential matches must say what to verify"
    assert match.sources, "criteria must cite their official source"


# --- Alerts: only exact SEC company IDs alert automatically -------------------


@pytest.mark.parametrize(
    ("basis", "decider"),
    list(itertools.product(LinkBasis, [None, ActorType.HUMAN, ActorType.MODEL])),
)
def test_only_exact_sec_id_links_alert_automatically(basis, decider):
    """Exhaustive over every link basis: if a change lets any non-SEC-ID link
    alert automatically (for example a fuzzy or model-approved match), this fails."""
    store = ReviewStore()
    item_id = None
    if decider is not None:
        item = store.add(ReviewItem(ReviewKind.RECORD_MATCH, "rec-1", "co-1", 0.9, (), (), now()))
        store.decide(item.item_id, Action.APPROVE_MERGE, "someone", decider)
        item_id = item.item_id
    linking = LinkResult(links={"rec-1": RecordLink("rec-1", "co-1", basis, item_id)})
    gate, _ = alert_gate("rec-1", "co-1", linking, store)
    assert (gate is AlertGate.AUTOMATIC) == (basis is LinkBasis.EXACT_CIK)


@pytest.mark.parametrize("action", [Action.REJECT_MERGE, Action.LEAVE_UNCERTAIN, None])
def test_unapproved_fuzzy_matches_never_alert_for_the_candidate(action):
    filing = form_d("Acme Robotics, Inc.", cik="0001")
    award = sbir("Acme Robotics", address=NEWARK)
    store = ReviewStore()
    link_records([filing, award], store)
    (item,) = store.items()
    if action is not None:
        store.decide(item.item_id, action, "Priya")
    result = link_records([filing, award], store)
    gate, _ = alert_gate(award.key, "cik:0001", result, store)
    assert gate in (AlertGate.BLOCKED, AlertGate.HOLD_FOR_REVIEW)
    if action is Action.REJECT_MERGE:
        assert gate is AlertGate.BLOCKED


# --- Alert feed: dedupe and exact-ID-only readiness --------------------------


def test_alert_feed_dedupes_and_only_exact_ids_are_ready():
    from gauge.alerts import AlertLog, AlertStatus, generate

    recs = [
        form_d("Acme Robotics, Inc.", cik="0001", filed=date(2025, 3, 1)),
        form_d("Acme Robotics, Inc.", cik="0001", filed=date(2026, 5, 1)),
        sbir("Acme Robotics", address=NEWARK, awarded=date(2026, 4, 1), phase=SbirPhase.PHASE_II),
    ]
    store, log = ReviewStore(), AlertLog()
    for _ in range(3):
        log.add(generate(run(recs, AS_OF, store), store, since=date(2026, 1, 1)))
    alerts = log.alerts()
    assert len({a.alert_id for a in alerts}) == len(alerts) == 2
    for a in alerts:
        linked_by_cik = a.record_key != recs[2].key
        assert (a.status is AlertStatus.READY) == linked_by_cik
