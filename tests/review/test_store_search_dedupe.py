from datetime import date

import pytest

from gauge.core.models import Address
from gauge.review import Action, ActorType, JsonReviewStore, ReviewStatus, ReviewStore, link_records
from gauge.review.dedupe import find_duplicate_companies, merge_approved_duplicates
from gauge.review.search import describe, search_companies
from tests.factories import form_d, profile, sbir

MONTCLAIR = Address(city="Montclair", state="NJ", postal_code="07042")


def _one_open_item(store):
    filing = form_d("Acme Robotics, Inc.", cik="0001")
    award = sbir("Acme Robotics", address=MONTCLAIR)
    link_records([filing, award], store)
    (item,) = store.items()
    return item


def test_json_store_persists_items_and_decision_history(tmp_path):
    path = tmp_path / "review.json"
    item = _one_open_item(JsonReviewStore(path))
    JsonReviewStore(path).decide(
        item.item_id, Action.LEAVE_UNCERTAIN, "Sam", note="need founder names"
    )
    JsonReviewStore(path).decide(item.item_id, Action.APPROVE_MERGE, "Priya")
    reloaded = JsonReviewStore(path).get(item.item_id)
    assert [d.actor for d in reloaded.decisions] == ["Sam", "Priya"]
    assert reloaded.decisions[0].note == "need founder names"
    assert reloaded.status is ReviewStatus.APPROVED
    assert reloaded.evidence == item.evidence


def test_decisions_must_name_an_actor():
    store = ReviewStore()
    item = _one_open_item(store)
    with pytest.raises(ValueError):
        store.decide(item.item_id, Action.APPROVE_MERGE, "  ")


def test_model_decision_details_are_kept():
    store = ReviewStore()
    item = _one_open_item(store)
    store.decide(
        item.item_id,
        Action.LEAVE_UNCERTAIN,
        "claude-opus-5",
        ActorType.MODEL,
        details={"rationale": "Different towns", "confidence": 0.4},
    )
    assert store.get(item.item_id).decisions[-1].details["rationale"] == "Different towns"
    assert not store.get(item.item_id).resolved_by_human


def test_search_by_name_id_record_and_town():
    acme = profile(form_d("Acme Robotics, Inc.", cik="0001"), company_id="cik:0001")
    zen = profile(sbir("Zenith Therapeutics", address=MONTCLAIR), company_id="rec:z")
    everyone = [acme, zen]
    assert search_companies(everyone, "acme")[0].profile is acme
    assert search_companies(everyone, "0001")[0].matched_on == "sec company id"
    award_id = zen.records[0].provenance.source_id
    assert search_companies(everyone, award_id)[0].profile is zen
    assert [h.profile for h in search_companies(everyone, town="Montclair")] == [zen]
    assert search_companies(everyone, "Zenith Therapeutic")[0].profile is zen
    assert search_companies(everyone, "nothing like it") == []


def test_describe_lists_linked_records():
    p = profile(form_d("Acme Robotics, Inc.", cik="0001"), sbir("Acme Robotics LLC"))
    text = "\n".join(describe(p))
    assert "0001" in text and "sbir_sttr" in text and "sec_form_d" in text


def test_duplicate_companies_are_proposed_then_merged_when_approved():
    a = profile(form_d("Northbeam Analytics Inc", cik="0007"), company_id="cik:0007")
    b = profile(sbir("Northbeam Analytics LLC"), company_id="rec:b")
    c = profile(sbir("Unrelated Materials"), company_id="rec:c")
    store = ReviewStore()
    (item,) = find_duplicate_companies([a, b, c], store)
    assert {item.subject, item.candidate_company_id} == {"cik:0007", "rec:b"}
    profiles = {p.company_id: p for p in (a, b, c)}
    assert len(merge_approved_duplicates(profiles, store)) == 3
    store.decide(item.item_id, Action.APPROVE_MERGE, "Priya")
    merged = merge_approved_duplicates(profiles, store)
    assert set(merged) == {"cik:0007", "rec:c"}
    assert len(merged["cik:0007"].records) == 2
    assert find_duplicate_companies([a, b, c], store) == []  # already resolved


def test_different_sec_ids_are_never_proposed_as_duplicates():
    a = profile(form_d("Northbeam Analytics Inc", cik="0007"), company_id="cik:0007")
    b = profile(form_d("Northbeam Analytics Inc", cik="0008"), company_id="cik:0008")
    assert find_duplicate_companies([a, b], ReviewStore()) == []


def test_rejected_duplicates_stay_separate():
    a = profile(sbir("Northbeam Analytics", awarded=date(2021, 1, 1)), company_id="rec:a")
    b = profile(sbir("Northbeam Analytics LLC"), company_id="rec:b")
    store = ReviewStore()
    (item,) = find_duplicate_companies([a, b], store)
    store.decide(item.item_id, Action.REJECT_MERGE, "Priya")
    assert len(merge_approved_duplicates({"rec:a": a, "rec:b": b}, store)) == 2
