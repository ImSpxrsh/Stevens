import json
from datetime import UTC, datetime

import pytest

from gauge.ai.claude import JsonResult
from gauge.ai.match_review import (
    PROMPT_VERSION,
    is_borderline,
    review_borderline,
)
from gauge.core.models import Address
from gauge.review import (
    Action,
    ActorType,
    AlertGate,
    LinkBasis,
    ReviewItem,
    ReviewKind,
    ReviewStatus,
    ReviewStore,
    alert_gate,
    link_records,
)
from tests.ai.fakes import FakeLLM, answer
from tests.factories import form_d, profile, sbir

NEWARK = Address(city="Newark", state="NJ", postal_code="07102")


def setup():
    filing = form_d("Acme Robotics, Inc.", cik="0001")
    award = sbir("Acme Robotics", address=NEWARK, abstract="SECRET-ABSTRACT-TEXT")
    records = [filing, award]
    store = ReviewStore()
    linking = link_records(records, store)
    (item,) = store.items()
    return records, store, linking, item, award


def run(llm, records, store, linking):
    return review_borderline(store, linking, records, llm)


def test_confident_match_is_a_model_approval_that_still_holds_alerts():
    records, store, linking, item, award = setup()
    (outcome,) = run(FakeLLM(answer("match", 0.95)), records, store, linking)
    assert outcome.action is Action.APPROVE_MERGE
    decision = store.get(item.item_id).decisions[-1]
    assert decision.actor_type is ActorType.MODEL and decision.actor == "claude-opus-5"

    relinked = link_records(records, store)
    assert relinked.links[award.key].basis is LinkBasis.MODEL_APPROVED
    gate, _ = alert_gate(award.key, "cik:0001", relinked, store)
    assert gate is AlertGate.HOLD_FOR_REVIEW


def test_confident_non_match_rejects():
    records, store, linking, item, _ = setup()
    run(FakeLLM(answer("not_a_match", 0.93)), records, store, linking)
    assert store.get(item.item_id).status is ReviewStatus.REJECTED


@pytest.mark.parametrize(
    "result",
    [
        answer("uncertain", 0.99),
        answer("match", 0.6),
        answer("not_a_match", 0.5),
        JsonResult({"decision": "maybe", "confidence": 0.9, "rationale": "x"}, "claude-opus-5"),
        JsonResult({"decision": "match", "confidence": 1.7, "rationale": "x"}, "claude-opus-5"),
        JsonResult({"decision": "match", "confidence": 0.95, "rationale": " "}, "claude-opus-5"),
        JsonResult(None, "claude-opus-5", error="refusal"),
        JsonResult(None, "claude-opus-5", error="connection_error"),
    ],
)
def test_uncertain_low_confidence_or_failed_output_stays_in_queue(result):
    records, store, linking, item, _ = setup()
    (outcome,) = run(FakeLLM(result), records, store, linking)
    assert outcome.action is Action.ANNOTATE
    stored = store.get(item.item_id)
    assert stored.status is ReviewStatus.OPEN
    assert stored in store.items(ReviewStatus.OPEN)
    # The model's opinion is recorded but it is not asked twice.
    assert run(FakeLLM(), records, store, linking)[0].asked is False


def test_decision_is_auditable():
    records, store, linking, item, _ = setup()
    llm = FakeLLM(answer("match", 0.97, "Same founders and topic."))
    run(llm, records, store, linking)
    details = store.get(item.item_id).decisions[-1].details
    assert details["prompt_version"] == PROMPT_VERSION
    assert details["served_model"] == "claude-opus-5"
    assert details["request_id"] == "req_test"
    assert details["rationale"] == "Same founders and topic."
    assert details["evidence"] == json.loads(llm.calls[0]["user"])
    assert len(details["evidence_sha256"]) == 64


def test_model_sees_structured_evidence_only():
    records, store, linking, _, award = setup()
    llm = FakeLLM(answer("uncertain", 0.5))
    run(llm, records, store, linking)
    sent = llm.calls[0]["user"]
    evidence = json.loads(sent)
    assert set(evidence) == {"name_similarity", "deterministic_signals", "subject", "candidate"}
    assert "SECRET-ABSTRACT-TEXT" not in sent  # abstracts are not sent
    assert award.provenance.source_url not in sent
    assert evidence["candidate"]["records"][0]["has_sec_company_id"] is True


def test_human_decided_items_are_never_sent():
    records, store, linking, item, _ = setup()
    store.decide(item.item_id, Action.LEAVE_UNCERTAIN, "Priya")
    llm = FakeLLM()
    assert run(llm, records, store, linking) == []  # not open, not listed
    assert llm.calls == []


def test_sec_company_ids_on_both_sides_are_never_sent():
    a = profile(form_d("Northbeam Analytics", cik="0007"), company_id="cik:0007")
    b = profile(form_d("Northbeam Analytics LLC", cik="0008"), company_id="cik:0008")
    item = ReviewItem(
        ReviewKind.DUPLICATE_COMPANIES, a.company_id, b.company_id, 0.97, (), (), datetime.now(UTC)
    )
    ask, why = is_borderline(item, (a, b))
    assert not ask and "SEC company IDs" in why


def test_exact_sec_id_links_ignore_any_model_decision():
    # A model "rejecting" a pair cannot split two filings that share an SEC company ID.
    a = form_d("Acme Robotics, Inc.", cik="0001")
    b = form_d("Totally Different Name", cik="0001")
    store = ReviewStore()
    result = link_records([a, b], store)
    assert result.links[b.key].basis is LinkBasis.EXACT_CIK
    assert store.items() == []


def test_limit_caps_model_calls():
    records, store, linking, _, _ = setup()
    llm = FakeLLM(answer("uncertain", 0.5))
    outcomes = review_borderline(store, linking, records, llm, limit=0)
    assert outcomes == [] and llm.calls == []
