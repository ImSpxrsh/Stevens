from datetime import date

from gauge.core.models import Address
from gauge.review import (
    Action,
    ActorType,
    AlertGate,
    LinkBasis,
    ReviewStatus,
    ReviewStore,
    alert_gate,
    auto_alert_allowed,
    link_records,
)
from tests.factories import form_d, sbir

HOBOKEN = Address(city="Hoboken", state="NJ", postal_code="07030")
NEWARK = Address(city="Newark", state="NJ", postal_code="07102")


def test_same_cik_merges_automatically_and_can_auto_alert():
    a = form_d("Acme Robotics, Inc.", cik="0001", filed=date(2021, 1, 1))
    b = form_d("ACME ROBOTICS INC", cik="0001", filed=date(2022, 1, 1))
    store = ReviewStore()
    result = link_records([a, b], store)
    assert len(result.profiles) == 1
    assert result.links[b.key].basis is LinkBasis.EXACT_CIK
    assert auto_alert_allowed(b.key, "cik:0001", result, store)
    assert store.items() == []


def test_same_name_and_postal_code_merges_but_does_not_auto_alert():
    filing = form_d("Acme Robotics, Inc.", cik="0001", address=HOBOKEN)
    award = sbir("Acme Robotics LLC", address=HOBOKEN)
    store = ReviewStore()
    result = link_records([filing, award], store)
    assert result.links[award.key].company_id == "cik:0001"
    assert result.links[award.key].basis is LinkBasis.EXACT_NAME_POSTAL
    gate, _ = alert_gate(award.key, "cik:0001", result, store)
    assert gate is AlertGate.HOLD_FOR_REVIEW


def test_fuzzy_match_opens_review_and_is_not_merged():
    filing = form_d("Acme Robotics, Inc.", cik="0001", address=HOBOKEN)
    award = sbir("Acme Robotic Systems", address=HOBOKEN)
    store = ReviewStore()
    result = link_records([filing, award], store, fuzzy_threshold=0.7)
    assert result.links[award.key].company_id != "cik:0001"
    (item,) = store.items()
    assert item.status is ReviewStatus.OPEN
    assert item.subject == award.key and item.candidate_company_id == "cik:0001"
    assert any("Same postal code" in r for r in item.reasons)
    assert award.provenance in item.evidence
    gate, reason = alert_gate(award.key, "cik:0001", result, store)
    assert gate is AlertGate.HOLD_FOR_REVIEW and item.item_id in reason


def test_approved_match_merges_on_next_run_and_is_attributed():
    filing = form_d("Acme Robotics, Inc.", cik="0001", address=HOBOKEN)
    award = sbir("Acme Robotics", address=NEWARK)
    store = ReviewStore()
    link_records([filing, award], store)
    (item,) = store.items()
    store.decide(item.item_id, Action.APPROVE_MERGE, "Priya", note="Same founders on both")
    result = link_records([filing, award], store)
    assert result.links[award.key].company_id == "cik:0001"
    assert result.links[award.key].basis is LinkBasis.HUMAN_APPROVED
    assert len(result.profile_for(award.key).records) == 2
    assert store.get(item.item_id).decisions[0].actor == "Priya"
    gate, _ = alert_gate(award.key, "cik:0001", result, store)
    assert gate is AlertGate.HUMAN_REVIEWED


def test_rejected_match_stays_separate_never_alerts_and_is_not_reproposed():
    filing = form_d("Acme Robotics, Inc.", cik="0001", address=HOBOKEN)
    award = sbir("Acme Robotics", address=NEWARK)
    store = ReviewStore()
    link_records([filing, award], store)
    (item,) = store.items()
    store.decide(item.item_id, Action.REJECT_MERGE, "Priya")
    result = link_records([filing, award], store)
    assert result.links[award.key].company_id != "cik:0001"
    assert alert_gate(award.key, "cik:0001", result, store)[0] is AlertGate.BLOCKED
    assert not auto_alert_allowed(award.key, "cik:0001", result, store)
    assert len(store.items()) == 1  # no duplicate review item


def test_model_approval_merges_but_still_needs_a_person_to_alert():
    filing = form_d("Acme Robotics, Inc.", cik="0001", address=HOBOKEN)
    award = sbir("Acme Robotics", address=NEWARK)
    store = ReviewStore()
    link_records([filing, award], store)
    (item,) = store.items()
    store.decide(item.item_id, Action.APPROVE_MERGE, "claude-opus-5", ActorType.MODEL)
    result = link_records([filing, award], store)
    assert result.links[award.key].basis is LinkBasis.MODEL_APPROVED
    assert alert_gate(award.key, "cik:0001", result, store)[0] is AlertGate.HOLD_FOR_REVIEW


def test_uncertain_decision_keeps_records_apart():
    filing = form_d("Acme Robotics, Inc.", cik="0001", address=HOBOKEN)
    award = sbir("Acme Robotics", address=NEWARK)
    store = ReviewStore()
    link_records([filing, award], store)
    (item,) = store.items()
    store.decide(item.item_id, Action.LEAVE_UNCERTAIN, "Priya")
    result = link_records([filing, award], store)
    assert result.links[award.key].company_id != "cik:0001"
    assert store.get(item.item_id).status is ReviewStatus.UNCERTAIN


def test_unrelated_names_start_their_own_company():
    filing = form_d("Acme Robotics, Inc.", cik="0001")
    award = sbir("Zenith Therapeutics")
    result = link_records([filing, award], ReviewStore())
    assert result.links[award.key].basis is LinkBasis.NEW_COMPANY
    assert len(result.profiles) == 2
