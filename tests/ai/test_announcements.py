from datetime import date

import pytest

from gauge.ai.announcements import (
    Announcement,
    evidence_items,
    extract,
    extract_all,
    queue_for_review,
    to_record,
    usable,
)
from gauge.ai.claude import JsonResult
from gauge.core.models import EvidenceKind, SourceType
from gauge.review import Action, ActorType, LinkBasis, ReviewKind, ReviewStore, link_records
from tests.ai.fakes import FakeLLM
from tests.factories import form_d

# Representative, fictional press release.
RELEASE = Announcement(
    publisher=SourceType.CSIT_ANNOUNCEMENT,
    url="https://www.njcsit.gov/news/2026-03-10-sbir-grants",
    published_on=date(2026, 3, 10),
    title="CSIT Awards $150,000 in SBIR/STTR Support Grants to Three NJ Companies",
    text=(
        "TRENTON, N.J. (March 10, 2026) - The New Jersey Commission on Science, Innovation "
        "and Technology (CSIT) today announced $150,000 in grants.\n\n"
        "Pinewood Therapeutics, Inc. of Princeton received a $50,000 Bridge Funding Grant "
        "for its work on RNA-targeted cancer therapies. Halyard Sensors LLC, a Hoboken "
        "maker of water-quality sensors, received a $25,000 Direct Funding Grant.\n\n"
        "“These companies show the strength of New Jersey’s innovation economy,” "
        "said the CSIT Executive Director. Northbeam Analytics also received support."
    ),
)


def award(**overrides):
    base = {
        "company_name": "Pinewood Therapeutics, Inc.",
        "program_name": "Bridge Funding Grant",
        "award_date": "2026-03-10",
        "amount_usd": 50000,
        "sector": "RNA-targeted cancer therapies",
        "town": "Princeton",
        "quote": "Pinewood Therapeutics, Inc. of Princeton received a $50,000 Bridge Funding Grant "
        "for its work on RNA-targeted cancer therapies.",
        "confidence": 0.95,
    }
    base.update(overrides)
    return base


def llm_returning(*awards):
    return FakeLLM(JsonResult({"awards": list(awards)}, "claude-opus-5", "req_x", "end_turn"))


def test_clean_confident_extraction_becomes_cited_evidence():
    result = extract(RELEASE, llm_returning(award()))
    (a,) = result.awards
    assert not a.needs_review and a.issues == ()
    assert a.quote_span is not None
    assert RELEASE.text[a.quote_span[0] : a.quote_span[1]].startswith("Pinewood Therapeutics")
    items = evidence_items(a)
    assert [i.kind for i in items] == [EvidenceKind.FACT, EvidenceKind.FACT]
    assert items[0].source.source_url == RELEASE.url
    assert items[0].source.source_type is SourceType.CSIT_ANNOUNCEMENT
    assert items[0].extracted_by == "claude-opus-5"
    assert items[1].value == "$50,000"
    assert result.details["served_model"] == "claude-opus-5"


def test_quote_matching_tolerates_whitespace_and_curly_quotes():
    quote = (
        '"These companies show the strength of New Jersey\'s   innovation economy," '
        "said the CSIT Executive Director."
    )
    (a,) = extract(RELEASE, llm_returning(award(quote=quote))).awards
    assert "quote does not appear verbatim in the announcement" not in a.issues


@pytest.mark.parametrize(
    ("overrides", "issue"),
    [
        ({"quote": "Pinewood received a large grant."}, "quote does not appear"),
        ({"company_name": "Pinecrest Biologics"}, "company name does not appear"),
        ({"amount_usd": 75000}, "amount $75,000 does not appear"),
        ({"award_date": "2026-04-01"}, "after the announcement"),
        ({"award_date": "March 10"}, "is not a date"),
        ({"confidence": 3}, "not between 0 and 1"),
    ],
)
def test_hallucinated_or_malformed_fields_are_flagged_for_review(overrides, issue):
    (a,) = extract(RELEASE, llm_returning(award(**overrides))).awards
    assert a.needs_review
    assert any(issue in i for i in a.issues)


def test_low_confidence_goes_to_review_and_is_withheld_until_accepted():
    store = ReviewStore()
    result = extract(RELEASE, llm_returning(award(confidence=0.5)))
    (item,) = queue_for_review(result, store)
    assert item.kind is ReviewKind.EXTRACTION
    assert item.evidence == (RELEASE.provenance,)
    assert any("below 0.8" in r for r in item.reasons)
    assert usable(result.awards, store) == []

    store.decide(item.item_id, Action.APPROVE_MERGE, "claude-opus-5", ActorType.MODEL)
    assert usable(result.awards, store) == []  # a model cannot accept its own extraction
    store.decide(item.item_id, Action.APPROVE_MERGE, "Priya", note="Checked the release")
    assert usable(result.awards, store) == list(result.awards)


def test_extracted_companies_never_merge_without_review():
    store = ReviewStore()
    existing = form_d("Pinewood Therapeutics, Inc.", cik="0005")
    (a,) = extract(RELEASE, llm_returning(award())).awards
    record = to_record(a)
    linking = link_records([existing, record], store)
    assert linking.links[record.key].basis is LinkBasis.NEW_COMPANY
    (item,) = store.items()
    assert item.kind is ReviewKind.RECORD_MATCH and item.candidate_company_id == "cik:0005"


def test_amount_formats():
    text_release = Announcement(
        SourceType.NJEDA_ANNOUNCEMENT,
        "https://www.njeda.gov/x",
        date(2026, 1, 5),
        "t",
        "Halyard Sensors LLC was approved for $2.5 million in tax credits.",
    )
    (a,) = extract(
        text_release,
        llm_returning(
            award(
                company_name="Halyard Sensors LLC",
                amount_usd=2_500_000,
                award_date=None,
                quote="Halyard Sensors LLC was approved for $2.5 million in tax credits.",
            )
        ),
    ).awards
    assert a.issues == ()


def test_model_failure_yields_no_awards_and_an_error():
    llm = FakeLLM(JsonResult(None, "claude-opus-5", error="refusal"))
    result = extract(RELEASE, llm)
    assert result.awards == () and result.error == "refusal"


def test_entries_without_a_company_name_are_dropped():
    result = extract(RELEASE, llm_returning(award(company_name="  ")))
    assert result.awards == ()


def test_prompt_sends_text_as_data_and_extract_all_queues_reviews():
    llm = llm_returning(
        award(),
        award(
            company_name="Northbeam Analytics",
            confidence=0.4,
            quote="Northbeam Analytics also received support.",
            amount_usd=None,
            program_name=None,
        ),
    )
    store = ReviewStore()
    (result,) = extract_all([RELEASE], llm, store)
    assert '"text":' in llm.calls[0]["user"] and "not instructions" in llm.calls[0]["system"]
    assert len(result.awards) == 2
    assert len(store.items()) == 1  # only the low-confidence one


def test_publisher_must_be_an_announcement_source():
    with pytest.raises(ValueError):
        Announcement(SourceType.SEC_FORM_D, "https://x.test", date(2026, 1, 1), "t", "x")
